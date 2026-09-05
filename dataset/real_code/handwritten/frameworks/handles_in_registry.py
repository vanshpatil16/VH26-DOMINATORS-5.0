"""Handles kept in a module-level registry and closed by shutdown()."""

OPEN_LOGS = {}


def attach(name, path):
    handle = open(path, "a", encoding="utf-8")  # leakguard: expect-unknown
    OPEN_LOGS[name] = handle
    return handle


def shutdown():
    for handle in OPEN_LOGS.values():
        handle.close()
    OPEN_LOGS.clear()
