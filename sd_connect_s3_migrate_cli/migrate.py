"""Main migration script."""

import os
import re
import typing
import json
import datetime

import aiohttp
import click
import anyascii

import tqdm

import boto3
import aioboto3
import aiobotocore.response

import botocore.exceptions
import botocore.config

import sd_lock_utility.types
import sd_lock_utility.exceptions
import sd_lock_utility.client
import sd_lock_utility.common
import sd_lock_utility.migrate
import sd_lock_utility.os_client
import sd_lock_utility.s3_client

import sd_connect_s3_migrate_cli.select
import sd_connect_s3_migrate_cli.types
import sd_connect_s3_migrate_cli.state


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


def init_opts(
    session: sd_lock_utility.types.SDAPISession,
    migration: sd_connect_s3_migrate_cli.types.MigrationEntry,
) -> sd_lock_utility.types.SDHeaderMigrate:
    """Initialize the required click opts dummy for the migration entry."""
    ret: sd_lock_utility.types.SDHeaderMigrate = {
        "container": migration["name"],
        "project_id": session["openstack_project_id"],
        "project_name": session["openstack_project_name"],
        "owner": "",
        "owner_name": "",
        "openstack_auth_url": session["openstack_auth_url"],
        "sd_connect_address": session["address"],
        "sd_api_token": session["token"],
        "prefix": "",
        "path": "",
        "no_preserve_original": False,
        "no_check_certificate": False,
        "progress": False,
        "debug": False,
        "verbose": False,
        "use_s3": True,
        "ec2_access_key": session["ec2_access_key"],
        "ec2_secret_key": session["ec2_secret_key"],
        "s3_endpoint_url": session["s3_endpoint_url"],
        "to_bucket": migration["convertedName"],
    }

    return ret


async def get_segmented_object_metadata(
    session: sd_lock_utility.types.SDAPISession, key: str
) -> sd_lock_utility.types.OpenstackObjectListingItem:
    """Retrieve the size for a segmented object."""
    return await sd_lock_utility.os_client.openstack_head_object(session, key)


async def parse_object(
    session: sd_lock_utility,
    object: sd_lock_utility.types.OpenstackObjectListingItem,
    segment_objects: list[sd_lock_utility.types.OpenstackObjectListingItem],
) -> sd_connect_s3_migrate_cli.types.MigrationObject:
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
                "bytes": segment_object["bytes"],
                "ETag": segment_object["hash"],
            }
            for segment_object in filter(
                lambda o: o["name"].startswith(
                    "/".join(migration_object["manifestBackup"].split("/")[1:])
                ),
                segment_objects,
            )
        ]

    return migration_object


async def wrap_stream_progress(
    body: aiobotocore.response.StreamingBody, t: tqdm.std.tqdm
) -> typing.AsyncGenerator[bytes, None]:
    """Wrap the stream progress in an iterator to display a progress bar."""
    async for chunk in body.iter_chunked(65564):
        t.update(len(chunk))
        yield chunk


async def copy_multipart_part_streaming(
    session: sd_lock_utility.types.SDAPISession,
    opts: sd_lock_utility.types.SDHeaderMigrate,
    migration_object: sd_connect_s3_migrate_cli.types.MigrationObject,
    migration_object_part: sd_connect_s3_migrate_cli.types.MigrationObjectPart,
    upload_id: str,
    progress_bar: tqdm.std.tqdm,
    dry_run: bool = False,
):
    """Copy a multipart part by streaming it through the host connection."""

    # Try generating the object url with standard boto3
    boto3_session = boto3.Session(
        aws_access_key_id=session["ec2_access_key"],
        aws_secret_access_key=session["ec2_secret_key"],
        region_name="default",
    )
    s3 = boto3_session.client("s3", endpoint_url=session["s3_endpoint_url"])
    object_url: str = s3.generate_presigned_url(
        ClientMethod="upload_part",
        Params={
            "Bucket": opts["to_bucket"],
            "Key": migration_object["key"],
            "PartNumber": int(migration_object_part["originalKey"].split("/")[-1]),
            "UploadId": upload_id,
            # "ChecksumMD5": migration_object_part["ETag"],
        },
        ExpiresIn=3600,
    )

    async with session["client"].get(
        f"{session['openstack_object_storage_endpoint']}/{migration_object['manifestBackup']}"
        + f"{migration_object_part['originalKey'].split('/')[-1]}",
        headers={
            "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(session),
        },
    ) as resp:
        if not dry_run:
            async with session["client"].put(
                object_url,
                headers={
                    # "Checksum-MD5": f"migration_object_part['ETag']",
                    "Content-Length": str(migration_object_part["bytes"]),
                },
                data=wrap_stream_progress(resp.content, progress_bar),
            ) as resp:
                pass
        else:
            progress_bar.update(int(resp.headers["Content-Length"]))


async def copy_object_streaming(
    session: sd_lock_utility.types.SDAPISession,
    opts: sd_lock_utility.types.SDHeaderMigrate,
    migration_object: sd_connect_s3_migrate_cli.types.MigrationObject,
    progress_bar: tqdm.std.tqdm,
    dry_run: bool = False,
):
    """Copy the object in full by streaming it through the host connection."""
    # Try generating the presigned url with standard boto3
    boto3_session = boto3.Session(
        aws_access_key_id=session["ec2_access_key"],
        aws_secret_access_key=session["ec2_secret_key"],
        region_name="default",
    )
    s3 = boto3_session.client(
        "s3",
        endpoint_url=session["s3_endpoint_url"],
        config=botocore.config.Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
        ),
    )
    object_url: str = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": opts["to_bucket"],
            "Key": migration_object["key"],
            # "ContentMD5": migration_object["ETag"],
        },
        ExpiresIn=3600,
    )

    async with session["client"].get(
        f"{session['openstack_object_storage_endpoint']}/{session['container']}/{migration_object['key']}",
        headers={
            "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(session),
        },
    ) as resp:
        if not dry_run:
            async with session["client"].put(
                object_url,
                headers={
                    # "Content-MD5": migration_object["ETag"],
                    "Content-Length": str(migration_object["bytes"]),
                },
                data=wrap_stream_progress(resp.content, progress_bar),
            ) as resp:
                pass
        else:
            progress_bar.update(int(resp.headers["Content-Length"]))


async def copy_multipart_part_hardware(
    session: sd_lock_utility.types.SDAPISession,
    opts: sd_lock_utility.types.SDHeaderMigrate,
    migration_object: sd_connect_s3_migrate_cli.types.MigrationObject,
    migration_object_part: sd_connect_s3_migrate_cli.types.MigrationObjectPart,
    upload_id: str,
    progress_bar: tqdm.std.tqdm,
    dry_run: bool = False,
):
    """Copy a multipart part by re-linking it in object storage."""
    if not dry_run:
        await session["s3_client"].upload_part_copy(
            Bucket=opts["to_bucket"],
            Key=migration_object["key"],
            PartNumber=int(migration_object_part["originalKey"].split("/")[-1]),
            UploadId=upload_id,
            CopySource={
                "Bucket": f"{migration_object['manifestBackup'].split("/")[0]}",
                "Key": migration_object_part["originalKey"],
            },
        )
    progress_bar.update(migration_object_part["bytes"])


async def copy_object_hardware(
    session: sd_lock_utility.types.SDAPISession,
    opts: sd_lock_utility.types.SDHeaderMigrate,
    migration_object: sd_connect_s3_migrate_cli.types.MigrationObject,
    progress_bar: tqdm.std.tqdm,
    dry_run: bool = False,
):
    """Copy the object in full by re-linking it in object storage."""
    if not dry_run:
        await session["s3_client"].copy_object(
            Bucket=opts["to_bucket"],
            Key=migration_object["key"],
            CopySource={"Bucket": session["container"], "Key": migration_object["key"]},
        )
    progress_bar.update(migration_object["bytes"])


async def wrap_object_copy(
    session: sd_lock_utility.types.SDAPISession,
    opts: sd_lock_utility.types.SDHeaderMigrate,
    migration_object: sd_connect_s3_migrate_cli.types.MigrationObject,
    s3accessible: bool,
    dry_run: bool = False,
):
    """Copy a whole object by streaming it through the host connection."""
    t = tqdm.tqdm(
        total=migration_object["bytes"],
        desc=f"Migrating file {migration_object['key']}",
        unit="iB",
        unit_scale=True,
        unit_divisor=1024,
        leave=False,
    )

    upload_id: str = ""

    try:
        if migration_object["isSegmented"]:
            try:
                mpu = await session["s3_client"].create_multipart_upload(
                    Bucket=opts["to_bucket"], Key=migration_object["key"]
                )
                upload_id = mpu["UploadId"]

                for migration_object_part in migration_object["multipartParts"]:
                    if s3accessible:
                        await copy_multipart_part_hardware(
                            session,
                            opts,
                            migration_object,
                            migration_object_part,
                            upload_id,
                            t,
                            dry_run,
                        )
                    else:
                        await copy_multipart_part_streaming(
                            session,
                            opts,
                            migration_object,
                            migration_object_part,
                            upload_id,
                            t,
                            dry_run,
                        )
            finally:
                try:
                    # Try finishing the multipart upload
                    await session["s3_client"].complete_multipart_upload(
                        Bucket=opts["to_bucket"],
                        Key=migration_object["key"],
                        UploadId=upload_id,
                        MultipartUpload={
                            "Parts": [
                                {
                                    "ETag": part["ETag"],
                                    "PartNumber": int(part["originalKey"].split("/")[-1]),
                                }
                                for part in migration_object["multipartParts"]
                            ]
                        },
                    )
                    migration_object["contentDone"] = True
                except Exception:
                    # In case there's a failure, abort the upload
                    await session["s3_client"].abort_multipart_upload(
                        Bucket=opts["to_bucket"],
                        Key=migration_object["key"],
                        UploadId=upload_id,
                    )
                    migration_object["contentDone"] = False
        else:
            try:
                if s3accessible:
                    await copy_object_hardware(
                        session, opts, migration_object, t, dry_run
                    )
                else:
                    await copy_object_streaming(
                        session, opts, migration_object, t, dry_run
                    )
                migration_object["contentDone"] = True
            except Exception:
                migration_object["contentDone"] = False
    finally:
        # Remember to wipe the object specific progress bar, as we don't need it
        t.close()

def handle_invalid_token(
    data_dir: str,
    session: sd_lock_utility.types.SDAPISession,
    migration: sd_connect_s3_migrate_cli.types.MigrationBucketList,
):
    click.echo("Invalid SD API token. Aborting.", err=True)
    # Clear token
    sd_connect_s3_migrate_cli.state.save_migration_state(
        data_dir,
        session["openstack_username"],
        b"",
        {
            "id": session["openstack_project_id"],
            "name": session["openstack_project_name"],
        },
        migration,
    )

async def initialize_conversion(
    username: str, keystone_host: str, data_dir: str, dry_run: bool
) -> int:
    """Initialize the required parameters for a conversion process."""
    ret = 0

    # Borrowing the relevant code and functionality from sd-lock-util
    # Initialize the session as empty, we'll populate it in a different order
    # than normal in sd-lock-util
    lock_util_session: sd_lock_utility.types.SDAPISession = (
        await sd_lock_utility.client.open_session(
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
    )
    # Add the client
    lock_util_session["client"] = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            ssl=sd_lock_utility.common.get_ssl_context(lock_util_session),
        ),
    )
    # Clear the auth url
    lock_util_session["openstack_auth_url"] = ""

    # Handle the possible previous migration
    previous_state: sd_connect_s3_migrate_cli.types.MigrationState = (
        sd_connect_s3_migrate_cli.state.load_migration_state(data_dir)  # type: ignore
    )
    continue_migration: bool = False
    if previous_state is not None:
        # Continuing from previous state
        click.echo(
            f"Discovered an interrupted migration for project {previous_state['project']['name']}"
        )
        click.echo(
            f"Previous migration was interrupted at {datetime.datetime.fromtimestamp(previous_state['timestamp']).isoformat()}"
        )
        click.echo("Following buckets are being migrated: ")
        for aborted_bucket in previous_state["buckets"]:
            click.echo(f"{aborted_bucket['name']} --> {aborted_bucket['convertedName']}")

        continue_migration = click.confirm(
            "Do you want to continue the interrupted migration?", default=False
        )

    # Retrieve the login infromation via CLI if it was not provided
    if continue_migration:
        lock_util_session["openstack_username"] = previous_state["username"]
    else:
        click.echo("Starting a new migration.")
        lock_util_session["openstack_username"] = os.environ.get("OS_USERNAME", username)
        if not lock_util_session["openstack_username"]:
            lock_util_session["openstack_username"] = click.prompt(
                "Please enter your Openstack username", default=""
            )

    lock_util_session["openstack_password"] = os.environ.get("OS_PASSWORD", "")
    lock_util_session["openstack_token"] = os.environ.get("OS_AUTH_TOKEN", "")
    if (
        not lock_util_session["openstack_password"]
        and not lock_util_session["openstack_token"]
    ):
        lock_util_session["openstack_password"] = click.prompt(
            "Please enter your Openstack password", default="", hide_input=True
        )
        if not lock_util_session["openstack_password"]:
            click.echo("No password was provided. Aborting.", err=True)
            return 1

    # Retrieve the Keystone auht URL via CLI if it was not provided
    lock_util_session["openstack_auth_url"] = os.environ.get("OS_AUTH_URL", keystone_host)
    if not lock_util_session["openstack_auth_url"]:
        lock_util_session["openstack_auth_url"] = click.prompt(
            "Please enter the authentication API address",
            default="https://pouta.csc.fi:5001/v3",
        )

    # Retrieve the SD Connect API address via CLI if it was not provided
    lock_util_session["address"] = os.environ.get("SD_CONNECT_API_ADDRESS", "")
    if not lock_util_session["address"]:
        lock_util_session["address"] = click.prompt(
            "Please enter the SD Connect API address", default="https://sd-connect.csc.fi"
        )
    if not lock_util_session["address"]:
        click.echo("No SD Connect API address was provided. Aborting.", err=True)

    # Select the project to use, unless it was provided
    lock_util_session["openstack_project_id"] = os.environ.get("OS_PROJECT_ID", "")
    lock_util_session["openstack_user_domain"] = os.environ.get(
        "OS_USER_DOMAIN_NAME", "Default"
    )

    if not lock_util_session["openstack_project_id"]:
        try:
            projects: sd_lock_utility.types.OpenstackProjectList = (
                await sd_lock_utility.os_client.openstack_get_projects(lock_util_session)
            )
        except sd_lock_utility.exceptions.Unauthorized:
            click.echo("Incorrect Openstack password. Aborting.", err=True)
            return
        except Exception:
            click.echo("Projects could not be retrieved. Aborting.", err=True)
            return


        if continue_migration:
            # Check that the interrupted migration project is available
            if previous_state["project"]["id"] not in [
                project["id"]
                for project in filter(
                    lambda project: project["id"] == previous_state["project"]["id"],
                    projects["projects"],
                )
            ]:
                click.echo(
                    f"Project {previous_state['project']['name']} not in projects listed in authentication."
                )
                if click.confirm(
                    "Do you want to cancel the previous migration and abort?",
                    default=True,
                ):
                    sd_connect_s3_migrate_cli.state.cancel_migration(data_dir)
                return 3

            lock_util_session["openstack_project_id"] = previous_state["project"]["id"]
            lock_util_session["openstack_project_name"] = previous_state["project"][
                "name"
            ]

        else:
            message = ""
            while True:
                project = sd_connect_s3_migrate_cli.select.select_projects(
                    projects["projects"], message
                )
                if project is None:
                    click.echo("Migration cancelled.")
                    return
                elif len(project) > 1:
                    message = "Please select only one project."
                elif len(project) == 0:
                    message = "Please select a project."
                else:
                    break

            lock_util_session["openstack_project_id"] = project[0]["id"]
            lock_util_session["openstack_project_name"] = project[0]["name"]

    click.echo(f"Selected project id: {lock_util_session['openstack_project_id']}")
    click.echo(f"Selected project name: {lock_util_session['openstack_project_name']}")

    # Retrieve the SD Connect API token via CLI if it was not provided
    sd_connect_api_token: str = os.environ.get("SD_CONNECT_API_TOKEN", "")
    if continue_migration:
        sd_connect_api_token = previous_state["apiToken"]
    if not sd_connect_api_token:
        sd_connect_api_token = click.prompt("Please enter the SD Connect API token")
    lock_util_session["token"] = sd_connect_api_token.encode("utf-8")

    # Clear the unscoped token from the openstack session and reauth
    lock_util_session["openstack_token"] = ""  # nosec
    try:
        await sd_lock_utility.os_client.openstack_get_token(lock_util_session)
    except Exception:
        click.echo("Failed to retrieve the scoped Openstack token. Aborting...", err=True)
        return 2

    # Select the buckets to migrate
    if not continue_migration:
        all_buckets: list[sd_connect_s3_migrate_cli.types.OpenstackBucket] = (
            await sd_lock_utility.os_client.get_containers(lock_util_session)
        )
        filtered_buckets = [b for b in all_buckets if not b["name"].endswith("_segments")]

        click.echo(f"Got in total {len(filtered_buckets)} buckets from the listing.")

        message = ""
        while True:
            buckets: list[sd_connect_s3_migrate_cli.types.OpenstackBucket] = (
                sd_connect_s3_migrate_cli.select.select_buckets(filtered_buckets, message)
            )

            if buckets is None:
                click.echo("Migration cancelled.")
                return
            elif len(buckets) < 1:
                message = "Please select at least one bucket for migration."
            else:
                break

        if len(buckets) > 1:
            click.echo(f"Selected {len(buckets)} for migration.")
        else:
            click.echo(f"Selected bucket \"{buckets[0]['name']}\" for migration.")

    bucket_sessions: dict[str, sd_lock_utility.types.SDAPISession] = {}

    # Initialize the migration status
    migration: sd_connect_s3_migrate_cli.types.MigrationBucketList = []
    if continue_migration:
        migration = previous_state["buckets"]

        for migration_bucket in migration:
            bucket_session = lock_util_session.copy()
            bucket_session["container"] = migration_bucket["name"]
            bucket_sessions[migration_bucket["name"]] = bucket_session
    else:
        for bucket in buckets:
            # Copy the bucket respective session for sd lock util
            bucket_session = lock_util_session.copy()
            bucket_session["container"] = bucket["name"]
            bucket_sessions[bucket["name"]] = bucket_session

            # Fetch a list of the bucket objects
            bucket_objects = await sd_lock_utility.os_client.get_container_objects(
                bucket_session, raw=True
            )
            segment_objects: list[sd_lock_utility.types.OpenstackObjectListingItem] = []

            bucket_bytes = bucket["bytes"]
            if segment_bucket := list(
                filter(lambda b: b["name"] == f"{bucket['name']}_segments", all_buckets)
            ):
                click.echo(
                    f"Matching segments bucket found for {bucket['name']}, caching segment bucket contents"
                )
                bucket_bytes += segment_bucket[0]["bytes"]
                segment_session = bucket_session.copy()
                segment_session["container"] = segment_session["container"] + "_segments"
                segment_objects = await sd_lock_utility.os_client.get_container_objects(
                    segment_session, raw=True
                )

            migration.extend(
                [
                    {
                        "name": bucket["name"],
                        "convertedName": convert_bucket_name(bucket["name"], "-conv"),
                        "bytes": bucket_bytes,
                        "bytesDone": 0,
                        "totalObjects": len(bucket_objects),
                        "totalObjectsDone": 0,
                        "totalHeaders": len(bucket_objects),
                        "totalHeadersDone": 0,
                        "currentlyMigrating": False,
                        "sharingMigrated": False,
                        "headersMigrated": False,
                        "currentlyMigratingFile": "",
                        "conversionNeed": int(
                            bucket["name"] != convert_bucket_name(bucket["name"], "-conv")
                        ),
                        "objects": [
                            await parse_object(bucket_session, o, segment_objects)
                            for o in bucket_objects
                        ],
                    }
                ]
            )

    sd_connect_s3_migrate_cli.state.save_migration_state(
        data_dir,
        lock_util_session["openstack_username"],
        lock_util_session["token"],
        {
            "id": lock_util_session["openstack_project_id"],
            "name": lock_util_session["openstack_project_name"],
        },
        migration,
    )

    # Migrate the contents of the buckets
    for migration_bucket in migration:
        if (
            migration_bucket["totalObjects"] == migration_bucket["totalObjectsDone"]
            and migration_bucket["sharingMigrated"]
            and migration_bucket["headersMigrated"]
        ):
            click.echo(f"Skipping bucket {migration_bucket['name']} as already migrated.")
            continue

        click.echo(f"Migrating bucket {migration_bucket['name']}")

        migration_bucket["currentlyMigrating"] = True

        # Initialize session and ec2 credentials
        session = bucket_sessions[migration_bucket["name"]]
        tmp_opts = init_opts(session, migration_bucket)
        await sd_lock_utility.os_client.init_s3_credentials(session)

        async with aioboto3.Session().client(
            service_name="s3",
            endpoint_url=session["s3_endpoint_url"],
            aws_access_key_id=session["ec2_access_key"],
            aws_secret_access_key=session["ec2_secret_key"],
        ) as s3:
            session["s3_client"] = s3

            # Migrate bucket objects
            ## Check if the bucket can be accessed using S3
            s3_accessible = True
            try:
                await sd_lock_utility.s3_client.s3_check_container(
                    session, tmp_opts, migration_bucket["name"]
                )
            except sd_lock_utility.exceptions.S3IncompatibleBucketName:
                s3_accessible = False
            except botocore.exceptions.ParamValidationError:
                s3_accessible = False
            ## Create the destination bucket if the bucket name changes
            if migration_bucket["name"] != migration_bucket["convertedName"]:
                try:
                    # Currently need to temporarily override the session bucket to force s3 to verify the new one
                    session["container"] = migration_bucket["convertedName"]
                    await sd_lock_utility.s3_client.s3_create_container(session, tmp_opts)
                    session["container"] = migration_bucket["name"]
                except sd_lock_utility.exceptions.Unauthorized:
                    handle_invalid_token(data_dir, lock_util_session, migration)
                    return

            ## Start the file migration
            for migration_object in tqdm.tqdm(
                migration_bucket["objects"],
                desc=f"Concatenating files to bucket {migration_bucket['convertedName']}",
            ):
                if migration_object["contentDone"]:
                    continue

                migration_bucket["currentlyMigratingFile"] = migration_object["key"]
                ## Migrate the object content
                await wrap_object_copy(
                    session, tmp_opts, migration_object, s3_accessible, dry_run
                )
                migration_bucket["totalObjectsDone"] += 1

                sd_connect_s3_migrate_cli.state.save_migration_state(
                    data_dir,
                    lock_util_session["openstack_username"],
                    lock_util_session["token"],
                    {
                        "id": lock_util_session["openstack_project_id"],
                        "name": lock_util_session["openstack_project_name"],
                    },
                    migration,
                )

            migration_bucket["currentlyMigratingFile"] = ""

            # Migrate bucket headers
            click.echo(f"Migrating headers for bucket {migration_bucket['name']}")
            if not dry_run and not migration_bucket["headersMigrated"]:
                try:
                    await sd_lock_utility.migrate.bucket_copy_headers(
                        tmp_opts, session.copy()
                    )
                except sd_lock_utility.exceptions.Unauthorized:
                    handle_invalid_token(data_dir, lock_util_session, migration)
                    return
                except sd_lock_utility.exceptions.NoKey:
                    click.echo("Failed to retrieve project public key for header migration.", err=True)

                migration_bucket["totalHeadersDone"] = len(migration_bucket["objects"])
                migration_bucket["headersMigrated"] = True
                for migration_object in migration_bucket["objects"]:
                    migration_object["headerDone"] = True

                sd_connect_s3_migrate_cli.state.save_migration_state(
                    data_dir,
                    lock_util_session["openstack_username"],
                    lock_util_session["token"],
                    {
                        "id": lock_util_session["openstack_project_id"],
                        "name": lock_util_session["openstack_project_name"],
                    },
                    migration,
                )

            # Migrate bucket sharing
            click.echo(f"Migrating sharing for bucket {migration_bucket['name']}")
            if not dry_run and not migration_bucket["sharingMigrated"]:
                try:
                    await sd_lock_utility.migrate.convert_bucket_acl(tmp_opts, session.copy())
                except sd_lock_utility.exceptions.Unauthorized:
                    handle_invalid_token(data_dir, lock_util_session, migration)
                    return

                migration_bucket["sharingMigrated"] = True

                sd_connect_s3_migrate_cli.state.save_migration_state(
                    data_dir,
                    lock_util_session["openstack_username"],
                    lock_util_session["token"],
                    {
                        "id": lock_util_session["openstack_project_id"],
                        "name": lock_util_session["openstack_project_name"],
                    },
                    migration,
                )

            migration_bucket["currentlyMigrating"] = False

            # Add the migration report to the bucket
            await session["s3_client"].put_object(
                Body=json.dumps(migration_bucket),
                Bucket=migration_bucket["convertedName"],
                Key="migration-report-latest.json",
            )

            sd_connect_s3_migrate_cli.state.save_migration_state(
                data_dir,
                lock_util_session["openstack_username"],
                lock_util_session["token"],
                {
                    "id": lock_util_session["openstack_project_id"],
                    "name": lock_util_session["openstack_project_name"],
                },
                migration,
            )

    click.echo("Migration finished, finishing the migration state.")
    sd_connect_s3_migrate_cli.state.finish_migration(data_dir)

    await lock_util_session["client"].close()

    return ret
