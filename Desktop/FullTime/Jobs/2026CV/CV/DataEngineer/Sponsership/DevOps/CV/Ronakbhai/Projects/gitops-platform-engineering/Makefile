.PHONY: test build render-dev render-staging render-prod validate

test:
	@echo "Running unit tests..."
	@echo "(placeholder - real repo runs the app's actual test suite here)"

build:
	docker build -t ghcr.io/org/sample-service:local .

render-dev:
	kubectl kustomize apps/sample-service/overlays/dev

render-staging:
	kubectl kustomize apps/sample-service/overlays/staging

render-prod:
	kubectl kustomize apps/sample-service/overlays/prod

validate:
	kubectl kustomize apps/sample-service/overlays/dev > /dev/null
	kubectl kustomize apps/sample-service/overlays/staging > /dev/null
	kubectl kustomize apps/sample-service/overlays/prod > /dev/null
	@echo "All overlays render successfully."
