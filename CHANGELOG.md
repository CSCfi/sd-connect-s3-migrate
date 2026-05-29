# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Calendar Versioning](https://calver.org/).

## [Unreleased]

### Changed

- (users) Updated Conversion Complete step with before and after bucket data (#70)
- (users) Updated text on Conversion in Process step (#72)
- (users) Updated text on API key step (#67)
- adjusted the estimated migration speed
- (users) updated time estimation
- (users) Updated login page text (#64)

### Added

- Prevent converted bucket name collision (#78)
- Retry header operations on failure (#76)
- Revert previous manifest if object copy fails (#77)
- (users) migration reports are now available in the migrated bucket after migration finishes.
- Prevent app suspension during migration (#60)
- Check existing bucket policy before sharing migration (#74)
- (users) Added progress bars in Conversion step (#71)
- (users) Added an alert for projects over 1 TB (#66)
- (users) The migration can now be resumed if the tool is closed prematurely, or crashes while migrating
- Add the migration state typing in JSDoc format
- Add the migration state hardcoded save location in the user `Documents` folder
- (users) Added Re-enter API key view (#38)

### Fixed

- Convert dots to dashes in bucket names (#79)

## [2026.4.19] - 2026-04-24

### Fixed

- wrong path in legacy build github action

### Added

- automatic version bumping on release

## [2026.4.18] - 2026-04-24

### Fixed

- added missing version tag to cli build pipeline
- Fix buckets with non-Latin letters in bucket name not tagged as urgent (#57)
- (users) Add forgotten links to docs (#63)

### Added

- cli legacy appimage build pipeline

## [2026.4.17] - 2026-04-17

### Removed

- (users) ARM windows builds no longer available due to issues with build automation

## [2026.4.16] - 2026-04-17

### Changed

- Github action no longer tries to run platform specific makers, letting forge to automatically pick the correct one

## [2026.4.15] - 2026-04-16

### Fixed

- explicitly define GITHUB_TOKEN in the publish step

## [2026.4.14] - 2026-04-16

### Added

- (users) Added links to instructions in user docs (#43)
- (users) Added end-of-year status to buckets

### Changed

- (users) packaged versions now point to SD Connect QA by default
- GitHub build pipeline now uses `@electron-forge/publish-github` for built-in publish support (watch out for regressions, may revert if necessary)
- dev mode application now points to SD Connect DEV by default

## [2026.4.13] - 2026-04-10

## [2026.4.12] - 2026-04-10

## [2026.4.11] - 2026-04-10

## [2026.4.10] - 2026-04-10

## [2026.4.9] - 2026-04-10

## [2026.4.8] - 2026-04-10

## [2026.4.7] - 2026-04-10

## [2026.4.6] - 2026-04-10

## [2026.4.5] - 2026-04-09

## [2026.4.4] - 2026-04-09

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


[Unreleased]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.19...HEAD
[2026.4.19]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.18...2026.4.19
[2026.4.18]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.17...2026.4.18
[2026.4.17]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.16...2026.4.17
[2026.4.16]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.15...2026.4.16
[2026.4.15]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.14...2026.4.15
[2026.4.14]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.13...2026.4.14
[2026.4.13]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.12...2026.4.13
[2026.4.12]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.11...2026.4.12
[2026.4.11]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.10...2026.4.11
[2026.4.10]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.9...2026.4.10
[2026.4.9]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.8...2026.4.9
[2026.4.8]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.7...2026.4.8
[2026.4.7]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.6...2026.4.7
[2026.4.6]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.5...2026.4.6
[2026.4.5]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.4...2026.4.5
[2026.4.4]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.3...2026.4.4
[2026.4.3]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.2...2026.4.3
[2026.4.2]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.1...2026.4.2
[2026.4.1]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/compare/2026.4.0...2026.4.1
[2026.4.0]: https://gitlab.ci.csc.fi/sds-dev/sd-connect/sd-connect-s3-migrate/-/releases/2026.4.0
