# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Calendar Versioning](https://calver.org/).

## [Unreleased]

### Added

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

- Fixed app flow between the steps (#11)
