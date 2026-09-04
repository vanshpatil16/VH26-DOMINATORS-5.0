"""A factory: ownership transfers to the caller, so we cannot prove anything."""

import sqlite3


def open_store(path):
    return sqlite3.connect(path)  # leakguard: expect-unknown


def open_log(path):
    handle = open(path, "a", encoding="utf-8")  # leakguard: expect-unknown
    return handle
