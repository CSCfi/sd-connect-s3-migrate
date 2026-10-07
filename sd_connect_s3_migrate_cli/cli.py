"""Main CLI implementation for the migration tool."""

import asyncio
import os
import sys
import traceback
import typing

import click

import sd_connect_s3_migrate_cli.migrate
import sd_connect_s3_migrate_cli.streams


@click.command()
@click.option("--username", default="", help="The CSC username to use when logging in.")
@click.option(
    "--keystone-host",
    default="",
    help="The Openstack (cPouta) authentication endpoint to use when logging in.",
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
    # addional file logging
    os.makedirs(data_dir, exist_ok=True)
    logfile = os.path.join(data_dir, "migration-logfile-cli.log")
    with open(logfile, "a", encoding="utf-8") as f:
        orig_stdout, orig_stderr = sys.stdout, sys.stderr
        sys.stdout = typing.cast(
            typing.TextIO, sd_connect_s3_migrate_cli.streams.Tee("[info] ", sys.stdout, f)
        )
        sys.stderr = typing.cast(
            typing.TextIO,
            sd_connect_s3_migrate_cli.streams.Tee("[error] ", sys.stderr, f),
        )

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
        except Exception:
            # Make sure traceback is captured in logfile
            traceback.print_exc(file=f)
            f.flush()
            raise
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            sys.stdout, sys.stderr = orig_stdout, orig_stderr

    sys.exit(ret)


@click.group()
def wrap():
    """Group CLI functions into a single tool to simplify using pyinstaller."""
    pass


wrap.add_command(convert)


if __name__ == "__main__":
    wrap()
