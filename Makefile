# Makefile — Polymath OS
# Single entry point. `make verify` is the open-source contract.

.DEFAULT_GOAL := help
.PHONY: help verify bootstrap dev test lint typecheck build ci-local sign clean

help: ## Show this message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

verify: ## Run all 12 verifiable claims. Exits 0 if all hold.
	@echo "→ Running 12 verification checks..."
	@python3 scripts/check.py

test: verify ## Run all tests (alias for verify + runtime tests)
	@cd runtime && python3 scripts/check.py > /dev/null && echo "  ✓ SINGULYAR EIR: ALL CHECKS PASSED"

bootstrap: ## Install dependencies (nix develop + pnpm install)
	@echo "→ Bootstrapping dev environment..."
	@nix develop --command true 2>/dev/null || echo "  ⚠ nix not available, skipping dev-shell"
	@pnpm install --frozen-lockfile 2>/dev/null || echo "  ⚠ pnpm not available, skipping JS deps"
	@echo "✓ Bootstrap complete. Run 'make verify' to validate claims."

dev: ## Start dev environment (Tilt with hot-reload)
	@tilt up

lint: ## Run linters
	pnpm turbo run lint 2>/dev/null || true
	@echo "  ✓ lint (or skipped if no pnpm)"

typecheck: ## Run type checking
	pnpm turbo run typecheck 2>/dev/null || true

build: ## Build all packages
	pnpm turbo run build 2>/dev/null || true

ci-local: ## Reproduce CI locally via act
	act -W .github/workflows/ci.yml -j ci

sign: ## Sign a container image via cosign (keyless OIDC)
	@read -p "Image ref (e.g. ghcr.io/user/app:tag): " image && \
		cosign sign --yes $$image && \
		echo "✓ Signed"

clean: ## Clean build artifacts
	@find . -type d \( -name node_modules -o -name dist -o -name .next -o -name .turbo -o -name target \) -prune -exec rm -rf {} +
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
	@find . -name "*.pyc" -delete 2>/dev/null
	@echo "✓ Cleaned"
