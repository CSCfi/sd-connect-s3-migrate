// Migration tool type definitions

// Type definitions for state and progress tracking
/**
 * @typedef {Object} MigrationObject
 * @property {string} key - The key of the object in object storage
 * @property {number} bytes - The size of the object in bytes
 * @property {boolean} headerDone - Flag if the object header has been migrated
 * @property {boolean} contentDone - Flag if the object content has been fully migrated
 * @property {boolean} isSegmented - Flag if the object is segmented or normal
 * @property {string} manifestBackup - Backup of the large object manifest string
 */

/**
 * @typedef {Object} MigrationEntry
 * @property {string} name - Name of the bucket that is flagged to be migrated
 * @property {number} totalObjects - The total amount of objects to be migrated
 * @property {number} totalObjectsDone - The amount of objects that have already been migrated
 * @property {number} totalHeaders - The total amount of headers to be migrated (typically same as amount of objects)
 * @property {number} totalHeadersDone - The amount of headers that have already been migrated
 * @property {boolean} currentlyMigrating - Flag if the bucket is currently being migrated
 * @property {boolean} sharingMigrated - Flag if the bucket sharing has been migrated
 * @property {boolean} headersMigrated - Flag if the bucket headers have been migrated
 * @property {string} currentlyMigratingFile - The file currently being migrated
 * @property {number} conversionNeed - Flag the level of incompatibiltiy of the bucket
 * @property {MigrationObject[]} objects - List of the objects to be migrated
 */

/**
 * @typedef {MigrationEntry[]} MigrationBucketList
 */

/**
 * @typedef {Object} OpenstackProject
 * @property {string} id - keystone id of the project
 * @property {string} name - keystone name of the project
 */

/**
 * @typedef {Object} MigrationState
 * @property {MigrationBucketList} - List of the buckets being migrated
 * @property {string} timestamp - Migration start date
 * @property {string} username - The migration user name
 * @property {string} apiToken - SD Connect API token
 * @property {OpenstackProject} project - the project being used for the migration
 */

// Type definitions for API results and communication
/**
 * @typedef {Object} OpenstackBucket
 * @property {number} count - amount of objects in the bucket
 * @property {number} bytes - total data stored in the bucket
 * @property {string} name - the name of the bucket
 * @property {string} last_modified - the date the bucket contents were last modified
 */
