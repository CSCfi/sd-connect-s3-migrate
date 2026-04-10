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
 * @typedef {MigrationEntry[]} MigrationState
 */
