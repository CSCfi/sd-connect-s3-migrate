"""CLI utility for converting SD Connect data to S3 compatible format.

The tool is meant to be used for converting SD Connect buckets and their
contents form an S3 incompatible format (SD Connect v1 and v2) to an
S3 compatible one (SD Connect v3). The tool renames the bucket according
to the S3 naming rules if necessary, concatenates the segmented objects
into S3 multipart objects, and converts the optional Swift ACL to an
S3 compatible bucket policy. Additionally the tool copies the encryption
headers and sharing in case the bucket name changes in conversion. See
CSC user guide for more thorough usage instructions.
"""

__name__ = "sd_connect_s3_migrate_cli"
__version__ = "2026.8.1"
__author__ = "CSC Developers"
__license__ = "MIT License"
