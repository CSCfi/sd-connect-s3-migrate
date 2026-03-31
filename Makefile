SHELL := /bin/bash

# Whitespace separated list of dependency:version, eg. "python:3.12", used for automatic dependency checking
# Dependencies without version are also supported, eg. "docker"
REQ_CMDS := node:22 npm:9 docker jq curl tar

# Build EVERYTHING by default
build-all:
	mkdir -p ./build
	@echo "Refreshing submodules"
	make refresh-submodules
	@echo "Checking dependencies"
	make check-deps
	@echo "Building BASH distributables"
	make build-bash-all
	@echo "Building CLI distributables"
	make build-cli-all
	@echo "Building GUI distributables"
	make build-gui-all

# Target for building all BASH distributables
build-bash-all:
	@echo "Building BASH migration script docker image"
	$(MAKE) -C sd_connect_s3_migrate_bash docker-distributable
	@echo "Building BASH migration script AppImage"
	$(MAKE) -C sd_connect_s3_migrate_bash legacy-appimage
	@echo "Copying the resulting binary to build folder"
	mkdir -p ./build/bash
	cp sd_connect_s3_migrate_bash/sd-connect-migrate-project-x86_64.AppImage ./build/bash/sd-connect-migrate-project-x86_64.AppImage

# Target for building all CLI distributables
build-cli-all:
	@echo "No CLI distributables to build."

# Target for building all GUI distributables
build-gui-all:
	@echo "Build GUI distributables"

check-deps:
	@for dep in $(REQ_CMDS); do \
		cmd="$${dep%%:*}"; \
		min="$${dep#*:}"; \
		if ! command -v $$cmd >/dev/null 2>&1; then \
			echo "Error: $$cmd is not installed or not in PATH"; \
			exit 1; \
		fi; \
		if [ "$$dep" = "$$cmd" ]; then \
			continue; \
		fi; \
		version="$$($$cmd --version 2>/dev/null | sed -E 's/[^0-9]*([0-9]+(\.[0-9]+)?).*/\1/')"; \
		if [ -z "$$version" ]; then \
			echo "Error: could not determine version for $$cmd"; \
			exit 1; \
		fi; \
		printf "%s\n%s\n" "$$min" "$$version" | sort -V -C || { \
			echo "Error: $$cmd must be >= $$min (currently $$version)"; \
			exit 1; \
		}; \
	done

refresh-submodules:
	git submodule foreach "git pull"
