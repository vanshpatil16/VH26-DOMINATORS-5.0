"""A yield-fixture: pytest guarantees the teardown half runs."""

import sqlite3

import pytest


@pytest.fixture
def connection():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


def test_roundtrip(connection):
    connection.execute("CREATE TABLE t (v INT)")
    connection.execute("INSERT INTO t VALUES (1)")
    assert connection.execute("SELECT v FROM t").fetchone() == (1,)
