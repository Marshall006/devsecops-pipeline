# ⚠️ Application VOLONTAIREMENT vulnérable

Ce dossier sert de **contre-épreuve** : chaque scanner de la chaîne DevSecOps
doit y trouver des failles. Le workflow `security-gate-demo.yml` vérifie que
c'est bien le cas : s'il ne détectait rien, c'est la chaîne qui serait cassée.

Ce code n'est jamais construit, publié ni déployé. Ne pas réutiliser.

| Faille injectée | Fichier | Détectée par |
|---|---|---|
| Injection SQL (requête construite avec une f-string) | `app.py` | Semgrep (SAST) |
| Injection de commande (`shell=True`) | `app.py` | Semgrep |
| Désérialisation non sûre (`pickle.loads`) | `app.py` | Semgrep |
| Exécution de code (`eval`) | `app.py` | Semgrep |
| Mode debug Flask en production | `app.py` | Semgrep |
| Dépendances avec CVE connues | `deps.lst` | pip-audit (SCA) |
| Image de base `latest`, exécution en root, `ADD` d'URL | `Dockerfile` | Hadolint, Trivy (IaC) |
