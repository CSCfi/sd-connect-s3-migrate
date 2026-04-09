# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Calendar Versioning](https://calver.org/).

## [Unreleased]

## [2026.4.3] - 2026-04-09

## [2026.4.2] - 2026-04-09

## [2026.4.1] - 2026-04-09

## [2026.4.0] - 2026-04-09

### Added

- automatic builds for distributables using a makefile
- (users) SD Connect v3 migration GUI can now copy over the Vault sharing when the bucket name changes to preserve `Collaborate` and `Transfer` access rights
- (users) SD Connect v3 migration GUI now supports migrating bucket headers when the bucket name changes to preserve file decryption access
- (users) SD Connect v3 migration GUI now supports migrating sharing from Swift ACLs to S3 bucket policies
- (users) CLI script can now be used to migrate bucket sharing as well
- use sd-lock-util sharing migration functionality to migrate sharing
- bash CLI tool now has scripts for building an AppImage of the script
- (users) a simple bash script for migrating urgent (containing whitespace) buckets in a single command
- a simple bash script for migrating urgent (containing whitespace) buckets in a single command
- Configure UI linting and formatting (#37)
- (users) the UI can now be used to copy over Swift objects to S3 compatible bucket naming scheme and file format
- bucket creation
- ec2 credential retrieval
- barebones migration progress tracking view
- barebones migration results view
- sharing ACL conversion from Swift ACL to AWS bucket policies
- object copy and multipart migration capability

### Changed

- Updated Conversion Complete step accordingly to Figma design (#29)
- Polish Data Conversion step accordingly to design (#28)
- Updated conversion need statuses
- Adjust Select buckets step accordingly to Figma design (#27)
- Adjust token step to Figma design (#26)
- Adjust project selection step accordingly to Figma (#25)
- Updated login view accordingly to Figma (#24)

### Fixed

- (users) migration bash script no longer uses incorrect project when first item on ec2 credential list is not owned by active project
- migration bash script no longer uses incorrect project when first item on ec2 credential list is not owned by active project
- Fixed app flow between the steps (#11)


[Unreleased]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.3...HEAD
[2026.4.3]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.2...2026.4.3
[2026.4.2]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.1...2026.4.2
[2026.4.1]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.0...2026.4.1
[2026.4.0]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/-/releases/2026.4.0
