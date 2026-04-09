# Make recipes for distributables for the bash script
# The recipes assume dependencies have already been checked


docker-distributable:
	@echo "Building the distributable docker image for running the migration script"
	docker build -t migration-docker .

legacy-appimage:
	@make legacy-build-image
	@echo "Using the build dockerimage to build a legacy (glibc>=2.30) AppImage version."
	@echo "The resulting binary will be in sd-connect-migrate-project-x86_64.AppImage"
	docker run --rm -v .:/src -it migration-bash-legacy-build

legacy-build-image:
	@echo "Building a docker image for building old glibc AppImage"
	docker build -f Dockerfile-build -t migration-bash-legacy-build .
