SHELL = /usr/bin/env bash
LANG = en_US.utf-8
PYTHON = $(shell which python3 || which python)
DOCKER = $(shell which docker)
DOCKER_COMPOSE = $(shell which docker || echo "$(DOCKER) compose")
DOCKER_COMPOSE_YAML = docker/docker-compose.yaml
export LANG

# Initializes submodules and copies environment file sample to env file.
.PHONY:init
init: .env
	poetry install 
	poetry run pre-commit install
	poetry run poe install-pyciemss 


.PHONY:tidy
tidy: 
	poetry run pre-commit run; \
	poetry run pytest

# Environment file copy
.env:
ifeq ($(wildcard envfile),)
	cp env.sample .env; \
	echo -e "\nDon't forget to update 'envfile' with all your secrets!";
endif

# Turn project on
.PHONY:up
up:docker/docker-compose.yaml
	$(DOCKER_COMPOSE) compose --profile standalone --file $(DOCKER_COMPOSE_YAML) up -d

# Rebuild all containers and turn project on
.PHONY:up-rebuild
up-rebuild:$(DOCKER_COMPOSE_YAML)
	$(DOCKER_COMPOSE) compose --profile standalone --file $(DOCKER_COMPOSE_YAML) up --build -d

# Rebuild the docker image from scratch
.PHONY:force-rebuild
force-rebuild:$(DOCKER_COMPOSE_YAML)
	$(DOCKER_COMPOSE) compose --profile standalone --file $(DOCKER_COMPOSE_YAML) build --no-cache

# Turn project off
.PHONY:down
down:$(DOCKER_COMPOSE_YAML)
	$(DOCKER_COMPOSE) compose --profile standalone --file $(DOCKER_COMPOSE_YAML) down

# Restart project
.PHONY:restart
restart:$(DOCKER_COMPOSE_YAML)
	make down && make up

