"""Main migration script."""


import os
import re

import aiohttp
import click
import anyascii

import sd_lock_utility.types
import sd_lock_utility.client
import sd_lock_utility.common
import sd_lock_utility.migrate
import sd_lock_utility.os_client
import sd_lock_utility.s3_client

import sd_connect_s3_migrate_cli.select
import sd_connect_s3_migrate_cli.types


def convert_bucket_name(bucket: str, bucket_suffix: str = "") -> str:
    """
    Convert the bucket name to a compatible one with best effort.
    """

    # 1. Transliterate Unicode -> ASCII
    slug = anyascii.anyascii(bucket)

    # 2. Replace all non [a-zA-Z0-9-] groups (incl spaces, punctuation, _, .)
    #    with a single dash, collapse repeats, and trim edges
    slug = re.sub(r"[^a-zA-Z0-9-]+", "-", slug).strip("-")

    # 3. Lowercase
    slug = slug.lower()

    # 4. Truncate to 63 characters (S3 max length)
    slug = slug[:63]

    # 5. If truncated slug ends with a dash, remove it
    if slug.endswith("-"):
        slug = slug[:-1]

    # 6. Ensure valid S3 boundaries (start/end alphanumeric)
    slug = re.sub(r"^[^a-z0-9]+", "", slug)
    slug = re.sub(r"[^a-z0-9]+$", "", slug)

    # 7. Return suffix if modified
    if bucket == slug:
        return slug
    else:
        return f"{slug}{bucket_suffix}"
    

async def get_segmented_object_metadata(session: sd_lock_utility.types.SDAPISession, key: str) -> sd_lock_utility.types.OpenstackObjectListingItem:
    """Retrieve the size for a segmented object."""
    return await sd_lock_utility.os_client.openstack_head_object(session, key)


async def parse_object(session: sd_lock_utility, object: sd_lock_utility.types.OpenstackObjectListingItem, segment_objects: list[sd_lock_utility.types.OpenstackObjectListingItem]) -> sd_connect_s3_migrate_cli.types.MigrationObject:
    """Parse a migration object from the openstack object listing."""
    migration_object: sd_connect_s3_migrate_cli.types.MigrationObject = {
        "key": object["name"],
        "bytes": object["bytes"],
        "headerDone": False,
        "contentDone": False,
        "isSegmented": False,
        "manifestBackup": "",
        "checksumSha256": "",
        "ETag": object["hash"],
        "multipartParts": [],
    }

    # Treating an empty object as segmented
    if object["bytes"] == 0:
        object_metadata = await get_segmented_object_metadata(session, object["name"])
        migration_object["bytes"] = object_metadata["bytes"]
        if object_metadata["manifest"]:
            migration_object["isSegmented"] = True
            migration_object["ETag"] = ""
            migration_object["manifestBackup"] = object_metadata["manifest"]

    # If the object is segmented, use existing segments as multipart parts
    if migration_object["isSegmented"]:
        migration_object["multipartParts"] = [
            {
                "key": migration_object["key"],
                "originalKey": segment_object["name"],
                "checksumSha256": "",
                "ETag": segment_object["hash"],
            } for segment_object in filter(lambda o: o["name"].startswith("/".join(migration_object["manifestBackup"].split("/")[1:])), segment_objects)
        ]

    return migration_object


async def initialize_conversion(username: str, keystone_host: str, data_dir: str) -> int:
    """Initialize the required parameters for a conversion process."""
    ret = 0

    # Borrowing the relevant code and functionality from sd-lock-util
    # Initialize the session as empty, we'll populate it in a different order
    # than normal in sd-lock-util
    lock_util_session: sd_lock_utility.types.SDAPISession = await sd_lock_utility.client.open_session(
        "placeholder-token",
        "placeholder-address",
        "placeholder-project-id",
        "placeholder-project-name",
        "placeholder-bucket",
        "placeholder-os-auth-url",
        "",
        "",
        "",
        "",
        "",
        False,
        True,
    )
    # Add the client
    lock_util_session["client"] = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            ssl=sd_lock_utility.common.get_ssl_context(lock_util_session),
        ),
    )
    # Clear the auth url
    lock_util_session["openstack_auth_url"] = ""

    # Retrieve the login infromation via CLI if it was not provided
    lock_util_session["openstack_username"] = os.environ.get("OS_USERNAME", username)
    if not lock_util_session["openstack_username"]:
        lock_util_session["openstack_username"] = click.prompt("Please enter your Openstack username", default="")

    lock_util_session["openstack_password"] = os.environ.get("OS_PASSWORD", "")
    lock_util_session["openstack_token"] = os.environ.get("OS_AUTH_TOKEN", "")
    if not lock_util_session["openstack_password"] and not lock_util_session["openstack_token"]:
        lock_util_session["openstack_password"] = click.prompt("Please enter your Openstack password", default="", hide_input=True)
        if not lock_util_session["openstack_password"]:
            click.echo("No password was provided. Aborting.", err=True)
            return 1

    # Retrieve the Keystone auht URL via CLI if it was not provided
    lock_util_session["openstack_auth_url"] = os.environ.get("OS_AUTH_URL", keystone_host)
    if not lock_util_session["openstack_auth_url"]:
        lock_util_session["openstack_auth_url"] = click.prompt("Please enter the authentication API address", default="https://pouta.csc.fi:5001/v3")
    
    # Retrieve the SD Connect API address via CLI if it was not provided
    lock_util_session["address"] = os.environ.get("SD_CONNECT_API_ADDRESS", "")
    if not lock_util_session["address"]:
        lock_util_session["address"] = click.prompt("Please enter the SD Connect API address", default="https://sd-connect.csc.fi")
    if not lock_util_session["address"]:
        click.echo("No SD Connect API address was provided. Aborting.", err=True)

    # Select the project to use, unless it was provided
    lock_util_session["openstack_project_id"] = os.environ.get("OS_PROJECT_ID", "")
    lock_util_session["openstack_user_domain"] = os.environ.get("OS_USER_DOMAIN_NAME", "Default")
    click.echo(lock_util_session)
    if not lock_util_session["openstack_project_id"]:
        projects: sd_lock_utility.types.OpenstackProjectList = await sd_lock_utility.os_client.openstack_get_projects(lock_util_session)
        while True:
            project = sd_connect_s3_migrate_cli.select.select_projects(projects["projects"])

            if len(project) > 1:
                click.echo(
                    "Migrating multiple projects at once is not yet supported. "
                    + "Please select your project again.",
                    err=True
                )
            else:
                break

        lock_util_session["openstack_project_id"] = project[0]["id"]
        lock_util_session["openstack_project_name"] = project[0]["name"]

    click.echo(f"Selected project id: {lock_util_session['openstack_project_id']}")
    click.echo(f"Selected project name: {lock_util_session['openstack_project_name']}")

    # Retrieve the SD Connect API token via CLI if it was not provided
    sd_connect_api_token: str = os.environ.get("SD_CONNECT_API_TOKEN", "")
    if not sd_connect_api_token:
        sd_connect_api_token = click.prompt("Please enter the SD Connect API token")

    # Clear the unscoped token from the openstack session and reauth
    lock_util_session["openstack_token"] = ""
    try:
        await sd_lock_utility.os_client.openstack_get_token(lock_util_session)
    except Exception:
        click.echo("Failed to retrieve the scoped Openstack token. Aborting...", err=True)
        return 2

    # Select the buckets to migrate
    all_buckets: list[sd_connect_s3_migrate_cli.types.OpenstackBucket] = await sd_lock_utility.os_client.get_containers(lock_util_session)

    click.echo(f"Got in total {len(all_buckets)} buckets from the listing.")

    while True:
        buckets: list[sd_connect_s3_migrate_cli.types.OpenstackBucket] = sd_connect_s3_migrate_cli.select.select_buckets(all_buckets)

        if len(buckets) < 1:
            click.echo("You must select at least one bucket for migration.", err=True)
        elif len(buckets) > 1:
            click.echo(f"Selected {len(buckets)} for migration.")
            break
        else:
            click.echo(f"Selected bucket \"{buckets[0]['name']}\" for migration.")
            break

    bucket_sessions: dict[str, sd_lock_utility.types.SDAPISession] = {}

    # Initialize the migration status
    migration: sd_connect_s3_migrate_cli.types.MigrationBucketList = []
    for bucket in buckets:
        # Copy the bucket respective session for sd lock util
        bucket_session = lock_util_session.copy()
        bucket_session["container"] = bucket["name"]
        bucket_sessions[bucket["name"]] = bucket_sessions

        # Fetch a list of the bucket objects
        bucket_objects = await sd_lock_utility.os_client.get_container_objects(bucket_session, raw=True)
        segment_objects: list[sd_lock_utility.types.OpenstackObjectListingItem] = []

        bucket_bytes = bucket["bytes"]
        if segment_bucket := list(filter(lambda b: b["name"] == f"{bucket['name']}_segments", all_buckets)):
            click.echo(f"Matching segments bucket found for {bucket['name']}, caching segment bucket contents")
            bucket_bytes += segment_bucket[0]["bytes"]
            segment_session = bucket_session.copy()
            segment_session["container"] = segment_session["container"] + "_segments"
            segment_objects = await sd_lock_utility.os_client.get_container_objects(segment_session, raw=True)

        migration.extend([{
            "name": bucket["name"],
            "convertedName": convert_bucket_name(bucket["name"]),
            "bytes": bucket_bytes,
            "bytesDone": 0,
            "totalObjects": len(bucket_objects),
            "totalObjectsDone": 0,
            "currentlyMigrating": False,
            "sharingMigrated": False,
            "headersMigrated": False,
            "currentlyMigratingFile": "",
            "conversionNeed": 0,
            "objects": [await parse_object(bucket_session, o, segment_objects) for o in bucket_objects],
        }])

    click.echo(migration)

    # Migrate the contents of the buckets

    return ret
