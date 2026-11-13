# Politique de sécurité

## Signaler une vulnérabilité

Merci de **ne pas ouvrir d'issue publique**. Utilisez le signalement privé de
GitHub : onglet **Security** > **Report a vulnerability**.

Réponse sous 72 heures ; correctif ou mesure d'atténuation sous 30 jours pour
une vulnérabilité confirmée.

## Vérifier l'authenticité d'une image

Toutes les images publiées sont signées (Sigstore keyless) et accompagnées
d'un SBOM et d'une provenance SLSA :

```bash
cosign verify ghcr.io/marshall006/invoice-api:main \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp '^https://github\.com/Marshall006/devsecops-pipeline/'

gh attestation verify oci://ghcr.io/marshall006/invoice-api:main --owner Marshall006
```
