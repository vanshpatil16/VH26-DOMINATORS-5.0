"""Load payload with the full try/except/else/finally ladder."""

import io
import logging


def telemetry_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.open(path, "rb")
    try:
        payload = handle.read(4096)
    except OSError:
        logging.warning("telemetry_file_binary failed")
        payload = None
    else:
        logging.debug("telemetry_file_binary ok")
    finally:
        handle.close()
    return payload
