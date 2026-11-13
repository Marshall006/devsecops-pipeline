# syntax=docker/dockerfile:1
# =============================================================================
# Image durcie, multi-stage, sur base Chainguard (« distroless ») :
#   - aucun shell, aucun gestionnaire de paquets dans l'image finale
#   - utilisateur non-root (UID 65532) par défaut
#   - quasi zéro CVE connue (images reconstruites quotidiennement)
# Analogie : on livre le plat dans une boîte scellée, sans la cuisine ni les
# couteaux qui ont servi à le préparer.
# =============================================================================

# Chainguard ne publie gratuitement que le tag « latest » : Dependabot épingle
# et met à jour le digest (voir .github/dependabot.yml).
# hadolint ignore=DL3007
FROM cgr.dev/chainguard/python:latest-dev AS build
WORKDIR /app
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
COPY --chown=65532:65532 requirements.txt .
# --require-hashes : chaque paquet doit correspondre à son empreinte SHA-256
# Les images Chainguard tournent en non-root (UID 65532) même pendant le build :
# les fichiers copiés doivent lui appartenir (--chown).
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY --chown=65532:65532 pyproject.toml .
COPY --chown=65532:65532 src ./src
RUN pip install --no-cache-dir --no-deps .
# Outils d'installation inutiles à l'exécution : on les retire de l'image
# finale (Trivy y avait détecté CVE-2025-47273 dans setuptools).
RUN pip uninstall -y setuptools pip

# hadolint ignore=DL3007
FROM cgr.dev/chainguard/python:latest
LABEL org.opencontainers.image.title="invoice-api" \
      org.opencontainers.image.description="API de calcul de factures, image durcie et signée" \
      org.opencontainers.image.source="https://github.com/Marshall006/devsecops-pipeline" \
      org.opencontainers.image.licenses="MIT"
WORKDIR /app
ENV PATH="/app/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=build /app/venv /app/venv
USER 65532
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
ENTRYPOINT ["uvicorn", "invoice_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
