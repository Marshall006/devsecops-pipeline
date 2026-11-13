#!/usr/bin/env bash
# =============================================================================
# Tests d'admission sur un vrai cluster Kubernetes avec Kyverno.
#
#   scripts/admission-tests.sh                 # politiques de configuration
#   scripts/admission-tests.sh <image@digest>  # + signature : l'image signée
#                                              #   est déployée, une image non
#                                              #   signée est refusée
#
# Les requêtes « --dry-run=server » passent par les contrôleurs d'admission
# (donc par Kyverno) sans rien créer réellement.
# =============================================================================
set -uo pipefail
SIGNED_IMAGE="${1:-}"
PODS="policies/tests/resources/pods.yaml"
# Image de NOTRE registre mais construite par un AUTRE pipeline (projet 1) :
# elle n'est pas signée par ce dépôt et doit donc être refusée.
UNSIGNED_IMAGE="ghcr.io/marshall006/credit-risk-api:sha-1e044913ea133283701446c05449b2a19dfb45b4"
failures=0
summary="${GITHUB_STEP_SUMMARY:-/dev/null}"
echo "| Test | Attendu | Résultat |" >> "$summary"
echo "|---|---|---|" >> "$summary"

pod() { yq "select(.metadata.name == \"$1\")" "$PODS"; }

expect_denied() {  # expect_denied <nom> <motif du message> <manifeste sur stdin>
  local name="$1" pattern="$2" out
  out=$(kubectl apply --dry-run=server -f - 2>&1)
  if [ $? -ne 0 ] && grep -q "$pattern" <<<"$out"; then
    echo "✔ refusé comme prévu : $name"; echo "| $name | refusé | ✅ refusé |" >> "$summary"
  else
    echo "✘ $name aurait dû être refusé par $pattern"; echo "$out"
    echo "| $name | refusé | ❌ $(head -c 120 <<<"$out") |" >> "$summary"; failures=$((failures+1))
  fi
}

expect_allowed() {  # expect_allowed <nom> <manifeste sur stdin>
  local name="$1" out
  if out=$(kubectl apply --dry-run=server -f - 2>&1); then
    echo "✔ accepté comme prévu : $name"; echo "| $name | accepté | ✅ accepté |" >> "$summary"
  else
    echo "✘ $name aurait dû être accepté"; echo "$out"
    echo "| $name | accepté | ❌ refusé |" >> "$summary"; failures=$((failures+1))
  fi
}

# 1. Politiques de configuration (la politique de signature est appliquée
#    ensuite, pour que chaque refus provienne bien de la politique testée)
kubectl create namespace apps --dry-run=client -o yaml | kubectl apply -f -
for f in policies/*.yaml; do
  [ "$(basename "$f")" = "require-signed-images.yaml" ] || kubectl apply -f "$f"
done
# Les webhooks Kyverno peuvent mettre quelques secondes à s'enregistrer
echo "Attente de l'activation des politiques…"
for _ in $(seq 1 40); do
  if pod bad-registry | kubectl apply --dry-run=server -f - 2>&1 | grep -q "restrict-image-registries"; then break; fi
  sleep 5
done

pod bad-latest     | expect_denied "Tag latest"             "disallow-latest-tag"
pod bad-registry   | expect_denied "Registre non autorisé"  "restrict-image-registries"
pod bad-privileged | expect_denied "Pod privilégié en root"  "pod-security-restricted"
pod bad-no-limits  | expect_denied "Sans limites mémoire"   "require-resources"

if [ -n "$SIGNED_IMAGE" ]; then
  # 2. Politique de signature
  kubectl apply -f policies/require-signed-images.yaml
  for _ in $(seq 1 40); do
    pod good | yq ".spec.containers[0].image = \"$UNSIGNED_IMAGE\"" \
      | kubectl apply --dry-run=server -f - 2>&1 | grep -q "require-signed-images" && break
    sleep 5
  done
  # Image non signée par ce pipeline -> refusée par la vérification Sigstore
  pod good | yq ".metadata.name = \"unsigned\" | .spec.containers[0].image = \"$UNSIGNED_IMAGE\"" \
    | expect_denied "Image non signée" "require-signed-images"

  # Image signée -> déploiement réel, puis appel de l'API
  sed "s|IMAGE_REF|$SIGNED_IMAGE|" deploy/invoice-api.yaml | expect_allowed "Image signée (dry-run)"
  sed "s|IMAGE_REF|$SIGNED_IMAGE|" deploy/invoice-api.yaml | kubectl apply -f -
  if kubectl -n apps rollout status deploy/invoice-api --timeout=180s; then
    kubectl -n apps port-forward svc/invoice-api 8080:80 >/dev/null 2>&1 &
    sleep 5
    if curl -sf localhost:8080/health; then
      echo; echo "✔ API signée déployée et fonctionnelle"
      echo "| Déploiement de l'image signée | en service | ✅ /health OK |" >> "$summary"
    else
      failures=$((failures+1)); echo "| Déploiement de l'image signée | en service | ❌ /health KO |" >> "$summary"
    fi
    kill %1 2>/dev/null || true
  else
    kubectl -n apps describe pods; kubectl get events -n apps
    failures=$((failures+1)); echo "| Déploiement de l'image signée | en service | ❌ rollout |" >> "$summary"
  fi
fi

echo "Échecs : $failures"
exit $failures
