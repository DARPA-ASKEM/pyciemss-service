SHELL = /bin/bash
LANG = en_US.utf-8
PYTHON = $(shell which python3 || which python)
DOCKER = $(shell which docker)
DOCKER_COMPOSE = $(shell which docker || echo "$(DOCKER) compose")
export LANG

# Initializes submodules and copies environment file sample to env file.
.PHONY:init
init:
	make envfile; \
	git submodule update --init; \

# Environment file copy
envfile:
ifeq ($(wildcard envfile),)
	cp api.env.sample api.env; \
	echo -e "\nDon't forget to update 'envfile' with all your secrets!";
endif

# Turn project on
.PHONY:up
up:docker-compose.yaml
	$(DOCKER_COMPOSE) compose up -d

# Rebuild all containers and turn project on
.PHONY:up-rebuild
up-rebuild:docker-compose.yaml
	$(DOCKER_COMPOSE) compose up --build -d

# Turn project off
.PHONY:down
down:docker-compose.yaml
	$(DOCKER_COMPOSE) compose down

# Restart project
.PHONY:restart
restart:docker-compose.yaml
	make down && make up

