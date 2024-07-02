# Variables
PROJECT_SLUG := auth-service
PORT := 2222

GREEN=$(shell tput -Txterm setaf 2)
YELLOW=$(shell tput -Txterm setaf 3)
RED=$(shell tput -Txterm setaf 1)
BLUE=$(shell tput -Txterm setaf 6)
RESET=$(shell tput -Txterm sgr0)

# Terminal
dev:
	uvicorn main:app --host 0.0.0.0 --port $(PORT)  --reload

format:
	black .
	ruff check --fix .

test:
	POSTGRES_SERVER=null PROJECT_NAME=null FIRST_SUPERUSER_FIRSTNAME=null FIRST_SUPERUSER_LASTNAME=null FIRST_SUPERUSER=email@email.com FIRST_SUPERUSER_PASSWORD=null python -m pytest


## Docker
startTest: ## Start docker development environment
	@echo "$(YELLOW)Starting docker environment...$(RESET)"
	docker compose -p $(PROJECT_SLUG) up --build

updateTest:  ## Update test environment containers (eg: after config changes)
	@echo "$(BLUE)Starting docker environment...$(RESET)"
	docker compose -p $(PROJECT_SLUG) up --build -d

stopTest: ## Stop test development environment
	@echo "$(RED)Removing docker environment...$(RESET)"
	@COMPOSE_PROJECT_NAME=$(PROJECT_SLUG) docker compose down


prep: ## Prepare postges database
	@echo "$(YELLOW)Preparing database...$(RESET)"
	./prestart.sh

prep-docker: ## Prepare postges database
	@echo "$(YELLOW)Preparing docker database...$(RESET)"
	docker exec auth-service-1 ./prestart.sh


pre-commit:
	npx concurrently --kill-others-on-fail --prefix "[{name}]" --names "backend:lint,backend:test" \
	--prefix-colors "bgRed.bold.white,bgGreen.bold.white,bgBlue.bold.white,bgMagenta.bold.white" \
	"docker exec auth-service-auth-1 make format" \
	"docker exec auth-service-auth-1 make test"