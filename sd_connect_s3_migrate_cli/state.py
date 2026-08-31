"""Functions required for handling the migration state save and load."""

import json
import os
import datetime
import time
import click

import sd_connect_s3_migrate_cli.types

CURRENT_STATE_NAME: str = "migration-state.json"


def save_migration_state(
    path: str,
    username: str,
    api_token: bytes,
    project: sd_connect_s3_migrate_cli.types.OpenstackProject,
    migration: sd_connect_s3_migrate_cli.types.MigrationBucketList,
):
    """Save the migration state to the requested location."""
    # Ensure that the path exists
    os.makedirs(path, exist_ok=True)

    migration_state: sd_connect_s3_migrate_cli.types.MigrationState = {
        "buckets": migration,
        "timestamp": int(time.time()),
        "username": username,
        "apiToken": api_token.decode("utf-8"),
        "project": project,
    }

    try:
        with open(f"{path}/{CURRENT_STATE_NAME}", "w") as state_file:
            state_file.write(json.dumps(migration_state))
    except OSError as e:
        click.echo("Failed to save migration state due to OS error.", err=True)
        click.echo(e)


def load_migration_state(
    path: str,
) -> sd_connect_s3_migrate_cli.types.MigrationState | None:
    """Load the migration state from the requested location."""
    try:
        with open(f"{path}/{CURRENT_STATE_NAME}", "r") as state_file:
            migration_state: sd_connect_s3_migrate_cli.types.MigrationState = json.loads(
                state_file.read()
            )

        migration_state["apiToken"] = migration_state["apiToken"]

        return migration_state
    except OSError:
        # Assuming there is no migration state to read if the read fails.
        return None


def cancel_migration(path: str):
    """Override the currently present migration state as cancelled."""
    try:
        os.rename(
            f"{path}/{CURRENT_STATE_NAME}",
            f"{path}/migration-state-canceled-{datetime.datetime.now().isoformat()}.json",
        )
    except OSError as e:
        click.echo("Failed to rename the canceled migration state.", err=True)
        click.echo(e)


def finish_migration(path: str):
    """Finish the ongoing migration state."""
    try:
        os.rename(
            f"{path}/{CURRENT_STATE_NAME}",
            f"{path}/migration-state-finished-{datetime.datetime.now().isoformat()}.json",
        )
    except OSError as e:
        click.echo("Failed to rename the finished migration state.", err=True)
        click.echo(e, err=True)
