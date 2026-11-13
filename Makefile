# Lancer localement les mêmes contrôles que la CI
TRIVY = docker run --rm -v "$(PWD):/src" -w /src aquasec/trivy:0.76.2

.PHONY: test sast sca iac image verify hooks

test:   ## Tests unitaires
	cd app && pytest -v

sast:   ## Analyse statique du code
	semgrep scan --config p/python --config p/owasp-top-ten --error app/src

sca:    ## Vulnérabilités des dépendances
	pip-audit -r app/requirements.txt --require-hashes --disable-pip

iac:    ## Dockerfile et manifestes Kubernetes
	docker run --rm -i hadolint/hadolint:v2.12.0 < app/Dockerfile
	$(TRIVY) config . --skip-dirs demo --skip-dirs policies/tests --severity HIGH,CRITICAL

image:  ## Construit et scanne l'image
	docker build -t invoice-api:local app
	docker save invoice-api:local -o image.tar
	$(TRIVY) image --input image.tar --severity HIGH,CRITICAL --ignore-unfixed

verify: ## Vérifie la signature de l'image publiée
	cosign verify ghcr.io/marshall006/invoice-api:main \
	  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
	  --certificate-identity-regexp '^https://github\.com/Marshall006/devsecops-pipeline/'

hooks:  ## Installe les hooks pre-commit (gitleaks, ruff…)
	pip install pre-commit && pre-commit install
