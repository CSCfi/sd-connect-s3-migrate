FROM debian:13

SHELL ["/bin/bash", "-lc"]

# Install the required packages
RUN apt-get update \
	&& apt-get -y upgrade \
	&& apt-get -y install git curl python3 python3-pip rclone jq

# Install `sd-lock-util`
RUN pip3 install --break-system-packages \
	gnureadline \
	python-openstackclient \
	git+https://github.com/CSCfi/sd-lock-util.git

# Install node
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
RUN \. "$HOME/.nvm/nvm.sh" && nvm install v22.22.2

# Install `transliteration` and `slugify` (and prune the first line of
# the script as there's a duplicate shebang)
RUN \. "$HOME/.nvm/nvm.sh" \
	&& npm i transliteration -g \
	&& sed -i 1d "/root/.nvm/versions/node/v22.22.2/bin/slugify" \
	&& sed -i 1d "/root/.nvm/versions/node/v22.22.2/bin/transliterate"

# Copy over the migration script
RUN mkdir /script
COPY ./migrate_project_bash_src/migrate_project.sh /script/migrate_project.sh

WORKDIR /script
ENTRYPOINT /script/migrate_project.sh
