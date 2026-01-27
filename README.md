# SD Connect S3 Migration Utility
This repository contains the SD Connect S3 migration utility. There are
certain incompatibilities that make it difficult to use files uploaded
with the Openstack Swift API via S3 API on the Ceph object storage.
As such, now with the move away from the Swift API we need to add a
suitable tool to fix these compatibility issues between different file
versions and bucket layouts.

The tool provides a simple UI for starting the migration, and does the
following things:

1. Provide a list of buckets with status
	* needs to be migrated (bucket name fully incompatible with S3)
	* should probably be migrated (contains files split into segments)
	* doesn't need to be migrated (only contains files inside a single buckets, no segments)
2. Allows selecting the buckets to be migrated from the list
3. Displays the bucket migration status
4. After migrating the data, migrates the decryption headers under the new bucket
5. Provides verification that the files were correctly migrated
	* Verifies content checksums
	* Verifies that all files have a matching header if it existed in the first place

### Dependencies
The tool is built into a singular binary, that should not require any
additional dependencies. Both the CLI script and the UI should be
portable, and runable without admin permissions. If someone is in the
unfortunate position where their employer whitelists only specific
applications (even those that are portable and signed) ~thye're
rightfully SoL~ they're able to run the application on e.g. CSC servers
or a virtual desktop environment.
