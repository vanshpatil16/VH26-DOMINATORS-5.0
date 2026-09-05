"""Stage bytes in a temporary file."""

import tempfile


def stage(payload):
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(payload)
        return handle.name
