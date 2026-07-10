import typing


class MigrationObjectPart(typing.TypedDict):
    key: str
    bytes: int
    originalKey: str
    checksumSha256: typing.NotRequired[str]
    ETag: typing.NotRequired[str]


class MigrationObject(typing.TypedDict):
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


class OpenstackProject(typing.TypedDict):
    id: str
    name: str


class MigrationState(typing.TypedDict):
    buckets: MigrationBucketList
    timestamp: int
    username: str
    apiToken: str
    project: OpenstackProject


class OpenstackBucket(typing.TypedDict):
    count: int
    bytes: int
    name: str
    last_modified: str
