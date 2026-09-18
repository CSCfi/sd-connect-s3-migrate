"""Types for migrate cli."""

import typing


class MigrationObjectPart(typing.TypedDict):
    """S3 multipart part of a migration object."""

    key: str
    bytes: int
    originalKey: str
    checksumSha256: typing.NotRequired[str]
    ETag: typing.NotRequired[str]


class MigrationObject(typing.TypedDict):
    """Migration object information."""

    key: str
    bytes: int
    headerDone: bool
    contentDone: bool
    isSegmented: bool
    manifestBackup: str
    checksumSha256: typing.NotRequired[str]
    ETag: typing.NotRequired[str]
    multipartParts: list[MigrationObjectPart]


class MigrationEntry(typing.TypedDict):
    """Migration information."""

    name: str
    convertedName: str
    bytes: int
    bytesDone: int
    totalObjects: int
    totalObjectsDone: int
    totalHeaders: int
    totalHeadersDone: int
    currentlyMigrating: bool
    sharingMigrated: bool
    headersMigrated: bool
    currentlyMigratingFile: str
    conversionNeed: int
    objects: list[MigrationObject]


MigrationBucketList = list[MigrationEntry]


class MigrationDeletedItemChecksum(typing.TypedDict):
    """Checksum entry of a migration deleted item."""

    type: typing.Literal["md5", "sha256"]
    checksum: str


class MigrationDeletedPart(typing.TypedDict):
    """Migration deletion entry for a MultipartPart."""

    key: str
    oldBucket: str
    newBucket: str
    deleted: bool
    checksum: MigrationDeletedItemChecksum | None


class MigrationDeletedItem(MigrationDeletedPart):
    """Migration deletion entry."""

    parts: list[MigrationDeletedPart]


MigrationDeleteList = list[MigrationDeletedItem]


class OpenstackProject(typing.TypedDict):
    """Openstack project information."""

    id: str
    name: str


class MigrationState(typing.TypedDict):
    """Current state of migration."""

    buckets: MigrationBucketList
    timestamp: int
    username: str
    apiToken: str
    project: OpenstackProject


class OpenstackBucket(typing.TypedDict):
    """Openstack bucket information."""

    count: int
    bytes: int
    name: str
    last_modified: str
