#!/bin/env bash
set -e


# Gather the variables from the environment
: ${OS_USERNAME:=""}
: ${OS_USER_DOMAIN_NAME:=""}
: ${OS_PASSWORD:=""}
: ${OS_PROJECT_ID:=""}
: ${OS_PROJECT_NAME:=""}
: ${OS_PROJECT_DOMAIN_ID:=""}
: ${OS_INTERFACE:="public"}
: ${OS_IDENTITY_API_VERSION:="3"}
: ${OS_AUTH_URL:=""}

: ${SD_CONNECT_API_ADDRESS:=""}
: ${SD_CONNECT_API_TOKEN:=""}


REQ_CMDS="node:22 npm:9 sd-lock-util rclone openstack jq slugify"

RCLONE_CONFIG="$PWD/.rclone-config-$OS_PROJECT_ID"


# Check the dependencies for the script
checkDependencies() {
    for dep in $REQ_CMDS; do
        cmd="${dep%%:*}";
		min="${dep#*:}";

		if !command -v $cmd > /dev/null 2>&1; then
			echo "Error: $cmd is not installed or not in PATH";
			exit 1;
		fi

		if [ "$dep" = "$cmd" ]; then
			continue;
		fi

		version="$($cmd --version 2>/dev/null | sed -E 's/[^0-9]*([0-9]+(\.[0-9]+)?).*/\1/')";
		if [ -z "$version" ]; then
			echo "Error: could not determine version for $cmd";
			exit 1;
		fi

		printf "%s\n%s\n" "$min" "$version" | sort -V -C || { \
			echo "Error: $cmd must be >= $min (currently $version)"; \
			exit 1; \
		}; \
	done
}


# Generate the configuration for rclone from template
generateRclone() {
	# Retrieve the EC2 credentials for the project
	if [ -z "$(openstack ec2 credential list -f value | head -n 1)" ]; then
		openstack ec2 credential create 
	fi

	# Can't be bothered to parse saved input to save API requests
	# First item is the access key id
	ec2_access=$(openstack ec2 credential list -f value | head -n 1 | tr -s '[:blank:]' '\n' | sed '1q;d')
	# Second item is the secret access key
	ec2_secret=$(openstack ec2 credential list -f value | head -n 1 | tr -s '[:blank:]' '\n' | sed '2q;d')

	# Retrieve the endpoint from the service catalog
	s3_endpoint=$(openstack catalog show object-store -f json | jq -r '.endpoints[] | select( .interface == "public").url' | sed "s/\/swift\/v1//g")

	cat > $RCLONE_CONFIG <<EOF
[$OS_PROJECT_ID-swift]
type = swift
user = $OS_USERNAME
key = $OS_PASSWORD
auth = $OS_AUTH_URL
tenant = $OS_PROJECT_NAME
tenant_id = $OS_PROJECT_ID
auth_version = 3
domain = $OS_USER_DOMAIN_NAME
tenant_domain = $OS_PROJECT_DOMAIN_ID

[$OS_PROJECT_ID]
type = s3
provider = Ceph
access_key_id = $ec2_access
secret_access_key = $ec2_secret
endpoint = $s3_endpoint
acl = private

EOF
}


# Convert bucket name into an s3 compatible format
convertBucketName() {
	suffix="-converted"
	max=63
	base_max=$((max - ${#suffix}))

	slug=$(slugify "$1" | tr -s '-' | sed 's/^-*//;s/-*$//')

	base=${slug:0:$base_max}
	base=${base%-}   # strip trailing hyphen before suffix

	final="${base}${suffix}"

	echo "$final"
}


echo "Checking that the required dependencies exist within the environment..."
checkDependencies

echo "Generating rclone configuration for $OS_PROJECT_NAME"
generateRclone

# Support passing buckets via command line to allow manually defining migrated buckets
# Note, bash struggles with whitespace, so for whitespace buckets it's safer to use the
# automatic option.
if [[ $# -gt 0 ]]; then
	echo "List of buckets provided, using it instead of whole project"
	echo "Buckets to be migrated: $*"
	MIGRATE_BUCKETS="$*"
else
	echo "No list of buckets provided, retrieving buckets from openstack"
	echo "Functionality to migrate non-urgent buckets will be added later"
	mapfile -t MIGRATE_BUCKETS < <(openstack container list -f value | grep "[[:space:]]" | grep -v "_segments")
	echo "The following buckets need to be urgently migrated:"
	for bucket in "${MIGRATE_BUCKETS[@]}"; do
		convertedBucket=$(convertBucketName "$bucket")
		echo "$bucket -> $convertedBucket)"
	done
fi

echo "Start bucket migration? [y/N] " && read ans && [ ${ans:-N} = y ]
echo "Started bucket migration"

for bucket in "${MIGRATE_BUCKETS[@]}"; do
	convertedBucket=$(convertBucketName "$bucket")
	echo "Migrating bucket: $bucket to $(convertBucketName $convertedBucket)"

	# Migrate the bucket contents
	echo "Migrating bucket contents..."
	rclone --config $RCLONE_CONFIG copy --progress "$OS_PROJECT_ID-swift:$bucket" "$OS_PROJECT_ID:$convertedBucket"
	
	# Migrate the bucket headers
	if [[ -n SD_CONNECT_API_TOKEN && -n SD_CONNECT_API_ADDRESS ]]; then
		echo "Migrating bucket headers..."
		sd-lock-util migrate-headers --no-check-certificate "$bucket" "$convertedBucket"
	else
		echo "SD Connect API not configured, not migrating headers."
		echo "Set the environment variables SD_CONNECT_API_TOKEN and SD_CONNECT_API_ADDRESS to enable header migration."
	fi

	# TODO: implement sharing migration in sd-lock-util and use it		
done
