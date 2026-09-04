"""Extract a single member from an archive."""

import zipfile


def read_member(archive_path, member):
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(member) as handle:
            return handle.read()
