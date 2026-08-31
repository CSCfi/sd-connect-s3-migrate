"""Main CLI implementation for the migration tool."""

import asyncio
import os
import sys

import click

import sd_connect_s3_migrate_cli.migrate


@click.command()
@click.option(
    "--username", default="", help="The openstack username to use when logging in."
)
@click.option(
    "--keystone-host",
    default="",
    help="The openstack authentication endpoint to use when logging  in.",
)
@click.option(
    "--data-dir",
    default=os.path.expanduser("~/Documents/SD-Connect-S3-Migrate"),
    help="The location for log files and migration state files.",
)
@click.option(
    "--dry-run", is_flag=True, help="Toggle dry-run mode to not actually migrate files."
)
def convert(
    username: str,
    keystone_host: str,
    data_dir: str,
    dry_run: bool,
):
    """Convert project resources into an S3 compatible form."""
    try:
        ret = asyncio.run(
            sd_connect_s3_migrate_cli.migrate.initialize_conversion_client_wrapper(
                username,
                keystone_host,
                data_dir,
                dry_run,
            )
        )
    except KeyboardInterrupt:
        ret = 0

    sys.exit(ret)


@click.group()
def wrap():
    """Group CLI functions into a single tool to simplify using pyinstaller."""
    pass


wrap.add_command(convert)


if __name__ == "__main__":
    wrap()
