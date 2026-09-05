"""Load payload with the full try/except/else/finally ladder."""

import logging
import tempfile


def telemetry_file_scratch(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = tempfile.TemporaryFile()
    try:
        handle.write(payload)
    except OSError:
        logging.warning("telemetry_file_scratch failed")
        payload = None
    else:
        logging.debug("telemetry_file_scratch ok")
    finally:
        handle.close()
    return payload
