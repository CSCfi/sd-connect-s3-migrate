"""Functionality to purge the old files after successful migration."""

import hashlib

import click
import sd_lock_utility.os_client
import sd_lock_utility.types

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
    verbose: bool = False,
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
            if verbose or debug:
                click.echo(f"Bucket {bucket} successfully deleted.")


async def delete_object_segments(
    session: sd_lock_utility.types.SDAPISession,
    manifest: str,
    verbose: bool = False,
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
        if verbose or debug:
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
    await delete_bucket_if_empty(session, bucket, verbose, debug)


async def delete_migrated_part(
    session: sd_lock_utility.types.SDAPISession,
    migration: sd_connect_s3_migrate_cli.types.MigrationEntry,
    object: sd_connect_s3_migrate_cli.types.MigrationObject,
    part: sd_connect_s3_migrate_cli.types.MigrationObjectPart,
    verbose: bool,
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
        if verbose or debug:
            click.echo("Checksums don't match, leaving the original in place.")

    # Try deleting the segment bucket
    await delete_bucket_if_empty(session, old_bucket, verbose, debug)

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
    verbose: bool,
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
            if verbose or debug:
                click.echo("Checksums match for segmented file, deleting old segments.")
            await delete_object_segments(
                session, object["manifestBackup"], verbose, debug
            )
            deleted_item["deleted"] = True
        if old_checksum == new_checksum:
            if verbose or debug:
                click.echo("Checksums match, deleting old object.")
            if await delete_migrated_object(session, migration, object):
                deleted_item["deleted"] = True
        else:
            if verbose or debug:
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
                        verbose,
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
    hard: bool,
    verbose: bool,
    debug: bool,
) -> sd_connect_s3_migrate_cli.types.MigrationDeleteList:
    """Clean up the redundant data after migration."""
    deleted_items: sd_connect_s3_migrate_cli.types.MigrationDeleteList = []

    for migration in migrations:
        for object in migration["objects"]:
            deleted_object: sd_connect_s3_migrate_cli.types.MigrationDeletedItem = (
                await delete_migrated_item(
                    session,
                    migration,
                    object,
                    hard,
                    verbose,
                    debug,
                )
            )
            deleted_items.append(deleted_object)

        # Try deleting the original bucket if the bucket name changed
        if migration["name"] != migration["convertedName"]:
            click.echo("Deleting the original bucket if it is empty.")
            await delete_bucket_if_empty(session, migration["name"], verbose, debug)

    return deleted_items
