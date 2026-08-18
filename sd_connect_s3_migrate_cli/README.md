# SD Connect S3 Migration Utility – CLI
This is the CLI implemenetation of the SD Connect S3 migration tool. It is
meant to be used to migrate and/or convert buckets, objects and sharing from
previous versions of SD Connect to a format most compatible with SD Connect v3.
The tool matches the functionality of SD Connect S3 Mirgation GUI, but
implements the features as a command-line interface for more efficient
operation.

### Installation

#### via pip

> Creating a Python either via [venv](https://docs.python.org/3/library/venv.html) or [pyenv](https://github.com/pyenv/pyenv) is recommended to avoid polluting system packages.

You can install the command-line migration tool directly from Github via pip.
```
$ pip install git+https://github.com/CSCfi/sd-connect-s3-migrate
```

To install possible updates, you can run the following command in the environment
where the migration tool is installed.
```
$ pip install -U git+https://github.com/CSCfi/sd-connect-s3-migrate
```

#### via binaries

> If you're using a Linux distribution with older glibc versions (such as RHEL 8), download the `legacy` binary. The official version is built on Ubuntu 22.04, and will not run on any system using `glibc<2.35`.

A portable executable binary is provided for the following platforms:
- Linux (`glibc>=2.35`) `amd64` and `arm64`
- Linux (`glibc>=2.30`) `amd64` legacy version for RHEL 8 and derivatives
- Windows (2H22 and newer) `amd64` and `arm64`
- macos (v14+) `arm64`

1. Select the correct binary for the most recent cli release, for your specific platform.
2. Download and extract (if necessary) the binary, and put it in a location where you can execute it (locations specified in your `$PATH` are recommended for ease of use, e.g. `$HOME/bin`)
3. Optionally, link the command to some shorthand, like `sd-connect-migrate` to avoid writing the whole thing.

### Usage

#### pip installation
Two commands will be available after installation:

1. `sd-connect-s3-migrate-cli`
2. `sd-connect-s3-convert`

The first one is the full migration tool, containing a single command `convert`. The latter
command is just a shorthand for `sd-connect-s3-migrate-cli convert`.

A migration can be performed by simply running the command, and interactively providing
the requested migration. After selecting a project, providing an SD Connect API token
for the selected project, and selecting the buckets to migrate, migration begins
automatically.

The convert command accepts the following arguments:

```
Usage: sd-connect-s3-migrate-cli convert [OPTIONS]

  Convert project resources into an S3 compatible form.

Options:
  --username TEXT       The openstack username to use when logging in.
  --keystone-host TEXT  The openstack authentication endpoint to use when
                        logging  in.
  --data-dir TEXT       The location for log files and migration state files.
  --dry-run             Toggle dry-run mode to not actually migrate files.
  --help                Show this message and exit.
```

The default data directory is `$HOME/$DOCUMENTS/SD-Connect-S3-Migrate`, same as with
the migration GUI.

Additionally the tool supports retrieving configuration from environment variables, in case
providing it interactively is not possible (or there is a need for repeat operations).

The environment variables are:
```
OS_USERNAME – the username used when connecting to object storage
OS_PASSWORD – the password used when connecting to object storage
SD_CONNECT_API_TOKEN – the API token for authenticating with SD Connect API, created for the project used in migration
OS_AUTH_TOKEN – as an alternative for the password login, an unscoped token to authenticate with the object storage
OS_PROJECT_ID – pre-selected project ID for object storage (can also be selected interactively in the tool)
OS_AUTH_URL – (not needed in normal operation) authentication URL for Openstack
SD_CONNECT_API_ADDRESS (not needed in normal operation) URL for the SD Connect API
OS_USER_DOMAIN_NAME – (not needed in normal operation) domain for the openstack user
```

#### binary installation
Use the executable name (e.g. `sd-connect-s3-migrate-cli-2026.8.1`) to invoke the command
(provided the executable is in a location specified in your `$PATH`). Alternatively,
run your shell in the folder where the executable is so you have the command available.

The command will run the full CLI, i.e. the same command as `sd-connect-s3-migrate-cli`
runs when using the version installed with `pip`.

Note that you may encounter a warning due to running an unsigned binary. In case you're not
able to grant the required exception to run the tool, contact your organizations IT support.
