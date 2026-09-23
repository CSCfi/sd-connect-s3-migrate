"""Functionality to purge the old files after successful migration."""

import hashlib

import click
import sd_lock_utility.os_client
import sd_lock_utility.types
import tqdm

import sd_connect_s3_migrate_cli.types


async def calculate_segmented_object_checksum(
    session: sd_lock_utility.types.SDAPISession,
    manifest: str,
    debug: bool = False,
) -> str:
    """Calculate the sha256 checksum of a segmented object from manifest."""
    # Create a local session, as we need to edit the bucket configuration
    local_session = session.copy()

    bucket: str = manifest.split("/")[0]
    local_session["container"] = bucket

    prefix: str = manifest.replace(f"{bucket}/", "")
    objects: list[sd_lock_utility.types.OpenstackObjectListingItem] = (
        await sd_lock_utility.os_client.get_container_objects(
            local_session,
            prefix,
            raw=True,
        )
    )
    # Sort the objects by order number
    objects.sort(key=(lambda o: o["name"].split("/")[-1]))
    if debug:
        click.echo("Got the following segment objects:")
        click.echo(objects)

    # Create the hashing context
    h = hashlib.sha256()

    for object in objects:
        # Retrieve objects in order and concatenate the contents
        if debug:
            click.echo(
                f"Concatenating segment {object['name'].split("/")[-1]} to the hash instance."
            )
        async with local_session["client"].get(
            f"{local_session['openstack_object_storage_endpoint']}/{bucket}/{object['name']}",
            headers={
                "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(
                    local_session
                ),
            },
        ) as resp:
            # Read the body in 64K chunks
            async for chunk in resp.content.iter_chunked(65536):
                h.update(chunk)

    checksum: str = h.hexdigest()
    if debug:
        click.echo(f"Original object checksum: {checksum}")

    return checksum


async def calculate_object_checksum(
    session: sd_lock_utility.types.SDAPISession,
    bucket: str,
    key: str,
    debug: bool,
) -> str:
    """Calculate the sha256 checksum of a specified object."""
    # Create a local session, as we need to edit the bucket configuration
    local_session = session.copy()
    local_session["container"] = bucket

    # Create the hashing context
    h = hashlib.sha256()

    # We'll use the swift client to pull the object, since the bucket may be
    # inaccessible using s3
    async with local_session["client"].get(
        f"{local_session['openstack_object_storage_endpoint']}/{bucket}/{key}",
        headers={
            "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(
                local_session
            ),
        },
    ) as resp:
        # Read the body in 64K chunks
        async for chunk in resp.content.iter_chunked(65536):
            h.update(chunk)

    checksum: str = h.hexdigest()
    if debug:
        click.echo(f"Object checksum: {checksum}")

    return checksum


async def delete_bucket_if_empty(
    session: sd_lock_utility.types.SDAPISession,
    bucket: str,
    debug: bool = False,
):
    """Delete the marked bucket if it does not contain objects."""
    local_session = session.copy()
    local_session["container"] = bucket

    # No need to check if the bucket is empty, we can just try deleting it
    async with local_session["client"].delete(
        f"{local_session['openstack_object_storage_endpoint']}/{bucket}",
        headers={
            "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(
                local_session
            ),
        },
    ) as resp:
        if resp.status == 409:
            if debug:
                click.echo(f"Bucket {bucket} not yet empty, delete not successful.")
        else:
            if debug:
                click.echo(f"Bucket {bucket} successfully deleted.")


async def delete_object_segments(
    session: sd_lock_utility.types.SDAPISession,
    manifest: str,
    debug: bool = False,
):
    """Delete the segments of the object."""
    # Create a local session, as we need to edit the bucket configuration
    local_session = session.copy()

    bucket: str = manifest.split("/")[0]
    local_session["container"] = bucket

    prefix: str = manifest.replace(f"{bucket}/", "")
    objects: list[sd_lock_utility.types.OpenstackObjectListingItem] = (
        await sd_lock_utility.os_client.get_container_objects(
            local_session,
            prefix,
            raw=True,
        )
    )
    # Sort the objects by order number
    objects.sort(key=(lambda o: o["name"].split("/")[-1]))
    if debug:
        click.echo("Got the following segment objects:")
        click.echo(objects)

    for object in objects:
        # Delete the segment object
        if debug:
            click.echo(
                f"Deleting segment {object['name'].split("/")[-1]} from the bucket."
            )
        async with local_session["client"].delete(
            f"{local_session['openstack_object_storage_endpoint']}/{bucket}/{object['name']}",
            headers={
                "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(
                    local_session
                ),
            },
        ) as resp:
            if debug:
                click.echo(resp.status)

    # Try deleting the segments bucket
    await delete_bucket_if_empty(session, bucket, debug)


async def delete_migrated_part(
    session: sd_lock_utility.types.SDAPISession,
    migration: sd_connect_s3_migrate_cli.types.MigrationEntry,
    object: sd_connect_s3_migrate_cli.types.MigrationObject,
    part: sd_connect_s3_migrate_cli.types.MigrationObjectPart,
    debug: bool,
) -> sd_connect_s3_migrate_cli.types.MigrationDeletedPart:
    """Delete a single segment or multipart part moved in the migration."""
    local_session = session.copy()

    old_bucket: str = object["manifestBackup"].split("/")[0]

    deleted: bool = False

    # Retrieve the most recent checksum of the old part
    local_session["container"] = old_bucket
    if debug:
        click.echo(
            f"{local_session['openstack_object_storage_endpoint']}/{old_bucket}/{part['originalKey']}"
        )
    async with local_session["client"].head(
        f"{local_session['openstack_object_storage_endpoint']}/{old_bucket}/{part['originalKey']}",
        headers={
            "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(
                local_session
            ),
        },
    ) as resp:
        if debug:
            click.echo(resp.headers)
        old_checksum: str = resp.headers["ETag"]

    # Delete if the most recent part checksum matches the migrated part
    if old_checksum == part["ETag"]:
        if debug:
            click.echo(
                f"Checksums match, deleting original part {part['originalKey']} in {old_bucket}."
            )
        async with local_session["client"].delete(
            f"{local_session['openstack_object_storage_endpoint']}/{old_bucket}/{part['originalKey']}",
            headers={
                "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(
                    local_session
                ),
            },
        ) as resp:
            if resp.status == 204 or resp.status == 404:
                deleted = True
            if debug:
                click.echo(resp)
    else:
        if debug:
            click.echo("Checksums don't match, leaving the original in place.")

    # Try deleting the segment bucket
    await delete_bucket_if_empty(session, old_bucket, debug)

    return {
        "checksum": {
            "checksum": old_checksum,
            "type": "md5",
        },
        "key": part["key"],
        "deleted": deleted,
        "newBucket": migration["convertedName"],
        "oldBucket": old_bucket,
    }


async def delete_migrated_object(
    session: sd_lock_utility.types.SDAPISession,
    migration: sd_connect_s3_migrate_cli.types.MigrationEntry,
    object: sd_connect_s3_migrate_cli.types.MigrationObject,
) -> bool:
    """Delete the original object."""
    # Only try deleting the object if the bucket name has changed
    if migration["name"] != migration["convertedName"]:
        async with session["client"].delete(
            f"{session['openstack_object_storage_endpoint']}/{migration['name']}/{object['key']}",
            headers={
                "X-Auth-Token": await sd_lock_utility.os_client.openstack_get_token(
                    session
                ),
            },
        ) as resp:
            if resp.status == 204:
                return True
            elif resp.status == 404:
                # If the object doesn't exist, we count deletion as successful
                return True
            else:
                return False

    # Default to successful deletion if the name didn't change
    return True


async def delete_migrated_item(
    session: sd_lock_utility.types.SDAPISession,
    migration: sd_connect_s3_migrate_cli.types.MigrationEntry,
    object: sd_connect_s3_migrate_cli.types.MigrationObject,
    hard: bool,
    debug: bool,
) -> sd_connect_s3_migrate_cli.types.MigrationDeletedItem:
    """Delete a single file moved in the migration."""
    deleted_item: sd_connect_s3_migrate_cli.types.MigrationDeletedItem = {
        "key": object["key"],
        "oldBucket": migration["name"],
        "newBucket": migration["convertedName"],
        "checksum": None,
        "deleted": False,
        "parts": [],
    }

    if hard:
        # Calculate sha256 for the old object
        old_checksum: str = ""
        if object["manifestBackup"]:
            # If the object was segmented, manually concatenate the segments
            old_checksum = await calculate_segmented_object_checksum(
                session,
                object["manifestBackup"],
                debug,
            )
        else:
            # Calculate the object directly from the original
            old_checksum = await calculate_object_checksum(
                session,
                migration["name"],
                object["key"],
                debug,
            )

        # Calculate sha256 for the new object
        new_checksum = await calculate_object_checksum(
            session,
            migration["convertedName"],
            object["key"],
            debug,
        )
        if old_checksum == new_checksum and object["manifestBackup"]:
            if debug:
                click.echo("Checksums match for segmented file, deleting old segments.")
            await delete_object_segments(session, object["manifestBackup"], debug)
            deleted_item["deleted"] = True
        if old_checksum == new_checksum:
            if debug:
                click.echo("Checksums match, deleting old object.")
            if await delete_migrated_object(session, migration, object):
                deleted_item["deleted"] = True
        else:
            if debug:
                click.echo("Checksums don't match, leaving the old segments for now.")
    else:
        if object["multipartParts"]:
            for part in object["multipartParts"]:
                deleted_part: sd_connect_s3_migrate_cli.types.MigrationDeletedPart = (
                    await delete_migrated_part(
                        session,
                        migration,
                        object,
                        part,
                        debug,
                    )
                )
                deleted_item["parts"].append(deleted_part)
        # Let's always try to delete the migrated object
        if await delete_migrated_object(session, migration, object):
            deleted_item["deleted"] = True

    return deleted_item


async def clean_up_migration(
    session: sd_lock_utility.types.SDAPISession,
    migrations: sd_connect_s3_migrate_cli.types.MigrationBucketList,
    debug: bool,
) -> int:
    """Clean up the redundant data after migration."""
    ret: int = 0

    if click.confirm("Do you want to clean up the old files?", default=False):
        click.echo("Cleaning up the migrated files.")
        click.echo(
            """\
SD Connect S3 Migrate CLI has two methods of verifying migrated file contents
before deletion.

Hard verification downloads each migrated file, each original file, and compares
them before deleting the original file. Use this option if you cannot recover
the dataset you have migrated, as this option increases bandwidth usage heavily
and is slow.

Soft verification (default option) compares the reported checksums of the file parts
on Allas before deletion. It will verify that the data did not change during or after
migration, but may not catch the case where parts of the file are missing. You should
use this option if you have backup of the data and prefer to save bandwidth."""
        )
    else:
        click.echo(
            "Not cleaning up the migrated files. You can check the migrated files from "
            "the migration report in the bucket later."
        )
        return ret

    hard: bool = click.confirm("Use hard verification before deletion?", default=False)

    deleted_items: sd_connect_s3_migrate_cli.types.MigrationDeleteList = []

    deletion_progress = tqdm.tqdm(
        total=sum([migration["totalObjectsDone"] for migration in migrations]),
        desc="Verify and delete -",
        leave=False,
    )

    for migration in migrations:
        for object in migration["objects"]:
            deletion_progress.desc = (
                f"Verify and delete {migration['name']}/{object['key']}"
            )

            deleted_object: sd_connect_s3_migrate_cli.types.MigrationDeletedItem = (
                await delete_migrated_item(
                    session,
                    migration,
                    object,
                    hard,
                    debug,
                )
            )
            deleted_items.append(deleted_object)

            deletion_progress.update(1)

        # Try deleting the original bucket if the bucket name changed
        if migration["name"] != migration["convertedName"]:
            await delete_bucket_if_empty(session, migration["name"], debug)

    deletion_progress.close()

    # Get the successfully deleted object count
    total_deleted: int = len(list(filter(lambda i: i["deleted"], deleted_items)))
    # Get the successfully deleted segment count (only for successfully deleted objects)
    total_deleted_segments: int = sum(
        [
            len(list(filter(lambda i: i["deleted"], item["parts"])))
            for item in filter(lambda i: i["deleted"], deleted_items)
        ]
    )
    # Get the failed deletion count
    total_failed: int = len(list(filter(lambda i: not i["deleted"], deleted_items)))
    # Get the failed segment count (for otherwise successful objects)
    total_failed_segments: int = sum(
        [
            len(list(filter(lambda i: not i["deleted"], item["parts"])))
            for item in filter(lambda i: i["deleted"], deleted_items)
        ]
    )

    if total_deleted > 0:
        if total_deleted == 1:
            click.echo("Deleted a single file.")
        else:
            click.echo(f"Deleted {total_deleted} files in total.")
    else:
        click.echo("No files were deleted for some reason.")

    if total_deleted_segments > 0:
        if total_deleted_segments == 1:
            click.echo("Deleted a single segment.")
        else:
            click.echo(f"Deleted {total_deleted_segments} segments in total.")
    else:
        click.echo("No segments were deleted.")

    if total_failed > 0:
        # Using return code 5 for failed deletion
        ret = 5
        if total_failed == 1:
            click.echo("Failed to delete one file.", err=True)
        else:
            click.echo(f"Failed to delete {total_failed} files.", err=True)
        # Report the failed files
        for migrated_object in filter(lambda i: not i["deleted"], deleted_items):
            click.echo(
                f"Failed to delete {migrated_object['key']} in bucket {migrated_object['oldBucket']}."
            )
    if total_failed_segments > 0:
        # Using return code 5 for failed deletion
        ret = 5
        if total_failed_segments == 1:
            click.echo("Failed to delete one segment in a deleted file.", err=True)
        else:
            click.echo(
                f"Failed to delete {total_failed_segments} in deleted files.", err=True
            )
        # Report the failed segments in otherwise deleted files
        for successful_object in filter(lambda i: i["deleted"], deleted_items):
            for segment in filter(lambda i: not i["deleted"], successful_object["parts"]):
                click.echo(
                    f"Failed to delete part {segment['key']} from bucket {segment['oldBucket']}, part of object {successful_object['key']} in {successful_object['oldBucket']}."
                )

    return ret
