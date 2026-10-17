# Every command an AI agent (or human) needs. Run `make setup` once, then
# `make check` until it passes -- that is the definition of done.
.DEFAULT_GOAL := help

.PHONY: help setup fix lint hygiene workflows typecheck arch deps test check hooks clean

help: ## Show the available commands
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Install or refresh the development environment (idempotent)
	uv sync

fix: ## Auto-format and auto-fix everything that can be fixed
	uv run ruff check --fix .
	uv run ruff format .

lint: ## Check formatting and linting (no changes made)
	uv run ruff format --check .
	uv run ruff check .

hygiene: ## Validate YAML/TOML and common file hygiene (no changes made)
	uv run prek run check-added-large-files check-merge-conflict check-toml check-yaml detect-private-key --all-files

workflows: ## Lint the GitHub Actions workflow files
	uv run actionlint

typecheck: ## Type-check the project
	uv run ty check

arch: ## Enforce the layered architecture
	uv run lint-imports

deps: ## Check dependency hygiene (unused or missing dependencies)
	uv run deptry .

test: ## Run the test suite with the coverage gate
	uv run pytest --cov

check: hygiene workflows lint typecheck arch deps test ## Run every check; the definition of done
	@echo "All checks passed."

hooks: ## Install the git hooks (runs on every commit)
	uv run prek install

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .import_linter_cache .hypothesis .coverage mutants htmlcov dist
