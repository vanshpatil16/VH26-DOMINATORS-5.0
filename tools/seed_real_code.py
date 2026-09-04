"""Seed `dataset/real_code/handwritten/` — correct resource handling (label 0).

These are the negatives, and about half of them are deliberately *adversarial*:
code that reads as leaky in plain text but is provably fine. LEAKGUARD_SPEC.md
section 8 warns that a judge will probe with exactly this, and every false
positive here is a team disabling the tool by week two.

Samples whose correct verdict is UNKNOWN rather than SAFE (the handle escapes,
so ownership moves to the caller) carry an inline `expect-unknown` marker. They
are still label 0: no leak exists in the file.
"""

from __future__ import annotations

import os
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.corpus_lib import REAL_DIR, Sample, build_sample, write_manifest  # noqa: E402

HANDWRITTEN = os.path.join(REAL_DIR, "handwritten")

# (category, filename, edge_case_ids, note, source)
SAMPLES: List[Tuple[str, str, List[str], str, str]] = []


def add(category: str, name: str, edge_cases: List[str], note: str, source: str) -> None:
    SAMPLES.append((category, name, edge_cases, note, source.lstrip("\n")))


# --------------------------------------------------------------------------- #
# files/
# --------------------------------------------------------------------------- #

add("files", "with_basic.py", ["EC-CTX-01"], "canonical with-statement", '''
"""Read a config blob off disk."""


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()
''')

add("files", "with_multi_item.py", ["EC-CTX-02"], "A9: several managers in one with", '''
"""Copy one file to another using a single multi-item with."""


def copy(src, dst):
    with open(src, "rb") as source, open(dst, "wb") as target:
        target.write(source.read())
''')

add("files", "try_finally.py", ["EC-CF-05"], "close in finally covers the raise path", '''
"""Parse a file, releasing the handle even when parsing explodes."""

import json


def load_json(path):
    handle = open(path, encoding="utf-8")
    try:
        return json.load(handle)
    finally:
        handle.close()
''')

add("files", "early_return_closed.py", ["EC-CF-01"], "every early return closes first", '''
"""Early returns that each release the handle before leaving."""


def first_non_empty_line(path):
    handle = open(path, encoding="utf-8")
    try:
        for line in handle:
            if line.strip():
                return line.strip()
        return ""
    finally:
        handle.close()
''')

add("files", "conditional_open_closed.py", ["EC-ALIAS-04"], "A11: ternary open, one close", '''
"""Both branches of the ternary bind the same handle, which is then closed."""


def read_either(primary, fallback, use_primary):
    handle = open(primary) if use_primary else open(fallback)
    try:
        return handle.read()
    finally:
        handle.close()
''')

add("files", "loop_with_inside.py", ["EC-LOOP-01"], "acquisition inside loop, but managed", '''
"""One handle per iteration, each closed by the with-block."""


def total_size(paths):
    total = 0
    for path in paths:
        with open(path, "rb") as handle:
            total += len(handle.read())
    return total
''')

add("files", "fdopen_wrapper.py", ["EC-WRAP-01"], "A14: closing the wrapper closes the fd", '''
"""Wrap a raw descriptor; closing the wrapper closes the descriptor."""

import os
import tempfile


def write_temp(payload):
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return path
''')

add("files", "tempfile_managed.py", ["EC-CTX-01"], "NamedTemporaryFile via with", '''
"""Stage bytes in a temporary file."""

import tempfile


def stage(payload):
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(payload)
        return handle.name
''')

add("files", "zipfile_nested.py", ["EC-CTX-03"], "nested managers, inner and outer both released", '''
"""Extract a single member from an archive."""

import zipfile


def read_member(archive_path, member):
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(member) as handle:
            return handle.read()
''')

add("files", "comprehension_in_with.py", ["EC-SYNTAX-01"], "comprehension inside the managed block", '''
"""The comprehension runs inside the with-block, so the file is still owned."""


def head(path, limit=10):
    with open(path, encoding="utf-8") as handle:
        return [line for _index, line in zip(range(limit), handle)]
''')

# --------------------------------------------------------------------------- #
# network/
# --------------------------------------------------------------------------- #

add("network", "socket_with.py", ["EC-CTX-01"], "socket as a context manager", '''
"""Probe a TCP endpoint."""

import socket


def probe(host, port, timeout=2.0):
    with socket.create_connection((host, port), timeout=timeout) as connection:
        connection.sendall(b"ping")
        return connection.recv(64)
''')

add("network", "socket_try_finally.py", ["EC-CF-05"], "explicit socket lifecycle", '''
"""Bind a listener and hand back the accepted peer address."""

import socket


def accept_one(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("127.0.0.1", port))
        server.listen(1)
        _peer, address = server.accept()
        return address
    finally:
        server.close()
''')

add("network", "urlopen_closing.py", ["EC-CTX-04"], "A2: contextlib.closing around urlopen", '''
"""Fetch a URL through closing()."""

import contextlib
from urllib.request import urlopen


def fetch(url):
    with contextlib.closing(urlopen(url)) as response:
        return response.read()
''')

add("network", "session_with.py", ["EC-CTX-01"], "requests.Session as a manager", '''
"""Reuse one HTTP session across a batch of requests."""

import requests


def fetch_all(urls):
    with requests.Session() as session:
        return [session.get(url).status_code for url in urls]
''')

add("network", "socket_shutdown_then_close.py", ["EC-CLOSE-02"], "shutdown + close both count", '''
"""Graceful shutdown before close."""

import socket


def send_once(host, port, payload):
    connection = socket.create_connection((host, port))
    try:
        connection.sendall(payload)
    finally:
        connection.shutdown(socket.SHUT_RDWR)
        connection.close()
''')

add("network", "helper_closes_param.py", ["EC-INTER-01"], "A7: helper releases the argument", '''
"""The cleanup lives in a helper that is called on every path."""

import socket


def _shutdown(connection):
    connection.close()


def request(host, port, payload):
    connection = socket.create_connection((host, port))
    try:
        connection.sendall(payload)
        return connection.recv(1024)
    finally:
        _shutdown(connection)
''')

# --------------------------------------------------------------------------- #
# database/
# --------------------------------------------------------------------------- #

add("database", "sqlite_closing.py", ["EC-DB-01"], "closing() because with() only commits", '''
"""`with sqlite3.connect(...)` is a TRANSACTION manager, so wrap it in closing."""

import contextlib
import sqlite3


def count_rows(path, table):
    with contextlib.closing(sqlite3.connect(path)) as connection:
        cursor = connection.execute("SELECT COUNT(*) FROM " + table)
        return cursor.fetchone()[0]
''')

add("database", "sqlite_try_finally.py", ["EC-CF-05"], "explicit connection lifecycle", '''
"""Insert a row, releasing the connection on every path."""

import sqlite3


def insert(path, name):
    connection = sqlite3.connect(path)
    try:
        connection.execute("INSERT INTO people (name) VALUES (?)", (name,))
        connection.commit()
    finally:
        connection.close()
''')

add("database", "cursor_and_connection.py", ["EC-DB-02"], "nested resources, both released", '''
"""Both the connection and the cursor are released."""

import contextlib
import sqlite3


def fetch_names(path):
    with contextlib.closing(sqlite3.connect(path)) as connection:
        with contextlib.closing(connection.cursor()) as cursor:
            cursor.execute("SELECT name FROM people")
            return [row[0] for row in cursor.fetchall()]
''')

add("database", "pool_checkin.py", ["EC-OWN-04"], "borrowed handle returned, not closed", '''
"""A pooled connection is checked back in rather than closed."""

import contextlib


class Pool:
    def __init__(self, factory):
        self._factory = factory
        self._idle = []

    @contextlib.contextmanager
    def lease(self):
        connection = self._idle.pop() if self._idle else self._factory()
        try:
            yield connection
        finally:
            self._idle.append(connection)


def run_query(pool, sql):
    with pool.lease() as connection:
        return connection.execute(sql).fetchall()
''')

# --------------------------------------------------------------------------- #
# process/
# --------------------------------------------------------------------------- #

add("process", "popen_with.py", ["EC-PROC-01"], "A15: Popen used as a context manager", '''
"""Popen as a context manager waits and closes the pipes."""

import subprocess


def run(command):
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        return process.stdout.read()
''')

add("process", "popen_communicate.py", ["EC-PROC-02"], "communicate() reaps the child", '''
"""communicate() drains the pipes and reaps the process."""

import subprocess


def capture(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    stdout, _stderr = process.communicate(timeout=30)
    return stdout
''')

add("process", "pool_close_join.py", ["EC-POOL-01"], "pool closed and joined in finally", '''
"""A worker pool that is always closed and joined."""

import multiprocessing


def square_all(values):
    pool = multiprocessing.Pool(processes=2)
    try:
        return pool.map(abs, values)
    finally:
        pool.close()
        pool.join()
''')

add("process", "executor_with.py", ["EC-POOL-02"], "executor as a context manager", '''
"""ThreadPoolExecutor shuts down on block exit."""

import concurrent.futures


def fan_out(work, items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        return list(executor.map(work, items))
''')

# --------------------------------------------------------------------------- #
# concurrency/
# --------------------------------------------------------------------------- #

add("concurrency", "lock_with.py", ["EC-LOCK-01"], "lock released by the with-block", '''
"""A counter guarded by a lock."""

import threading


class Counter:
    def __init__(self):
        self._lock = threading.Lock()
        self._value = 0

    def increment(self):
        with self._lock:
            self._value += 1
            return self._value
''')

add("concurrency", "lock_try_finally.py", ["EC-LOCK-02"], "acquire/release around a raising body", '''
"""Explicit acquire with a matching release in finally."""

import threading

LOCK = threading.Lock()


def guarded(action):
    LOCK.acquire()
    try:
        return action()
    finally:
        LOCK.release()
''')

add("concurrency", "semaphore_with.py", ["EC-LOCK-01"], "semaphore as a manager", '''
"""Bound concurrent work with a semaphore."""

import threading


def limited(work, items, limit=4):
    gate = threading.Semaphore(limit)
    results = []
    for item in items:
        with gate:
            results.append(work(item))
    return results
''')

# --------------------------------------------------------------------------- #
# async_resources/
# --------------------------------------------------------------------------- #

add("async_resources", "session_async_with.py", ["EC-ASYNC-01"], "A13: correct async with", '''
"""Fetch a page with an aiohttp session that is always closed."""

import aiohttp


async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
''')

add("async_resources", "async_exit_stack.py", ["EC-ASYNC-02"], "AsyncExitStack owns the session", '''
"""AsyncExitStack unwinds every registered async resource."""

import contextlib

import aiohttp


async def fetch_one(url):
    async with contextlib.AsyncExitStack() as stack:
        session = await stack.enter_async_context(aiohttp.ClientSession())
        response = await session.get(url)
        return await response.text()
''')

add("async_resources", "async_try_finally.py", ["EC-ASYNC-03"], "awaited close in finally", '''
"""An asyncio stream pair closed on every path."""

import asyncio


async def ping(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b"ping")
        await writer.drain()
        return await reader.read(64)
    finally:
        writer.close()
        await writer.wait_closed()
''')

add("async_resources", "aiofiles_with.py", ["EC-ASYNC-01"], "async file manager", '''
"""Read a file without blocking the loop."""

import aiofiles


async def read_text(path):
    async with aiofiles.open(path, mode="r") as handle:
        return await handle.read()
''')

# --------------------------------------------------------------------------- #
# contextlib_patterns/
# --------------------------------------------------------------------------- #

add("contextlib_patterns", "exit_stack.py", ["EC-CTX-05"], "A1: ExitStack owns every handle", '''
"""ExitStack registers cleanup for a variable number of files."""

import contextlib


def concat(paths):
    with contextlib.ExitStack() as stack:
        handles = [stack.enter_context(open(path, encoding="utf-8")) for path in paths]
        return "".join(handle.read() for handle in handles)
''')

add("contextlib_patterns", "exit_stack_manual.py", ["EC-CTX-06"], "manually closed ExitStack", '''
"""An ExitStack that is closed explicitly rather than via with."""

import contextlib


def read_pair(first, second):
    stack = contextlib.ExitStack()
    try:
        left = stack.enter_context(open(first, encoding="utf-8"))
        right = stack.enter_context(open(second, encoding="utf-8"))
        return left.read(), right.read()
    finally:
        stack.close()
''')

add("contextlib_patterns", "generator_manager.py", ["EC-GEN-01"], "A3: cleanup after yield", '''
"""A hand-rolled context manager whose cleanup follows the yield."""

import contextlib


@contextlib.contextmanager
def opened(path):
    handle = open(path, encoding="utf-8")
    try:
        yield handle
    finally:
        handle.close()
''')

add("contextlib_patterns", "closing_helper.py", ["EC-CTX-04"], "closing() around a custom object", '''
"""closing() adapts anything with a close() to the with protocol."""

from contextlib import closing
from urllib.request import urlopen


def head_bytes(url, count=128):
    with closing(urlopen(url)) as response:
        return response.read(count)
''')

add("contextlib_patterns", "exit_stack_callback.py", ["EC-CTX-07"], "callback registration is cleanup", '''
"""stack.callback registers the close explicitly."""

import contextlib


def read_with_callback(path):
    with contextlib.ExitStack() as stack:
        handle = open(path, encoding="utf-8")
        stack.callback(handle.close)
        return handle.read()
''')

add("contextlib_patterns", "suppress_around_close.py", ["EC-CTX-08"], "suppress wraps the close", '''
"""Ignore an error raised *by* the close, without skipping it."""

import contextlib
import socket


def best_effort(host, port, payload):
    connection = socket.create_connection((host, port))
    try:
        connection.sendall(payload)
    finally:
        with contextlib.suppress(OSError):
            connection.close()
''')

# --------------------------------------------------------------------------- #
# class_ownership/
# --------------------------------------------------------------------------- #

add("class_ownership", "exit_closes_attr.py", ["EC-OWN-01"], "A5: __exit__ releases the attribute", '''
"""The class owns the connection and releases it in __exit__."""

import sqlite3


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.db.close()

    def names(self):
        return [row[0] for row in self.db.execute("SELECT name FROM people")]
''')

add("class_ownership", "close_method.py", ["EC-OWN-01"], "explicit close() releases the attribute", '''
"""A client whose close() releases the socket it owns."""

import socket


class Client:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port))

    def send(self, payload):
        self.sock.sendall(payload)

    def close(self):
        self.sock.close()
''')

add("class_ownership", "del_closes_attr.py", ["EC-OWN-02"], "__del__ counts as a closer", '''
"""Cleanup in __del__: fragile, but it is a closer and we recognise it."""

import sqlite3


class Cache:
    def __init__(self, path):
        self.db = sqlite3.connect(path)

    def get(self, key):
        return self.db.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()

    def __del__(self):
        self.db.close()
''')

add("class_ownership", "shutdown_closes_attr.py", ["EC-OWN-03"], "shutdown()/stop() are closers too", '''
"""A worker whose pool is released by shutdown()."""

import concurrent.futures


class Worker:
    def __init__(self, size=4):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=size)

    def submit(self, fn, *args):
        return self.pool.submit(fn, *args)

    def shutdown(self):
        self.pool.shutdown(wait=True)
''')

add("class_ownership", "manager_pair.py", ["EC-OWN-01"], "enter/exit pair on the owner", '''
"""Session object usable as a context manager."""

import requests


class ApiClient:
    def __init__(self, base):
        self.base = base
        self.session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.session.close()

    def get(self, path):
        return self.session.get(self.base + path)
''')

# --------------------------------------------------------------------------- #
# decoys/  — the regex killers
# --------------------------------------------------------------------------- #

add("decoys", "docstring_mentions_close.py", ["EC-DECOY-01"], "A6: docstring names close()", '''
"""Module whose prose talks about closing files."""


def load(path):
    """Read a file.

    Remember to call handle.close() when you are done, unless you use the
    with-statement below, which does it for you. Never write:

        handle = open(path)
        return handle.read()
    """
    with open(path, encoding="utf-8") as handle:
        return handle.read()
''')

add("decoys", "string_literal_code.py", ["EC-DECOY-02"], "leaky code inside a string constant", '''
"""The leaky snippet is data, not code."""

TEMPLATE = "handle = open(path)"

BAD_EXAMPLE = """
connection = sqlite3.connect(path)
return connection.execute(query)
"""


def render(path):
    with open(path, encoding="utf-8") as handle:
        return TEMPLATE + handle.read()
''')

add("decoys", "commented_out_leak.py", ["EC-DECOY-03"], "the leak is commented out", '''
"""A previous, leaky implementation survives only as a comment."""


def read(path):
    # handle = open(path)
    # return handle.read()
    with open(path, encoding="utf-8") as handle:
        return handle.read()
''')

add("decoys", "shadowed_open.py", ["EC-DECOY-04"], "a local open() that is not builtins.open", '''
"""A domain object with its own open() that acquires nothing."""


class Valve:
    def __init__(self):
        self.state = "shut"

    def open(self):
        self.state = "open"
        return self.state


def cycle(valve):
    valve.open()
    return valve.state
''')

add("decoys", "close_as_dict_key.py", ["EC-DECOY-05"], "close appears as data", '''
"""The word close is a dictionary key and a column name here."""

CANDLE = {"open": 101.5, "high": 104.0, "low": 100.2, "close": 103.7}


def spread(bar=CANDLE):
    return bar["high"] - bar["low"]


def summarise(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read(), CANDLE["close"]
''')

add("decoys", "non_resource_close.py", ["EC-DECOY-06"], "close() on a non-resource", '''
"""A ticket object with a close() that has nothing to do with descriptors."""


class Ticket:
    def __init__(self, ident):
        self.ident = ident
        self.closed = False

    def close(self):
        self.closed = True


def resolve(ident):
    ticket = Ticket(ident)
    ticket.close()
    return ticket
''')

# --------------------------------------------------------------------------- #
# frameworks/
# --------------------------------------------------------------------------- #

add("frameworks", "pytest_yield_fixture.py", ["EC-FW-01"], "A8: fixture cleanup after yield", '''
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
''')

add("frameworks", "flask_route_with.py", ["EC-FW-02"], "route handler with correct handling", '''
"""A request handler on the hot path, handled correctly."""

import contextlib
import sqlite3

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/people")
def list_people():
    with contextlib.closing(sqlite3.connect("app.db")) as connection:
        rows = connection.execute("SELECT name FROM people").fetchall()
    return jsonify([row[0] for row in rows])
''')

add("frameworks", "fastapi_dependency.py", ["EC-FW-03"], "dependency generator closes in finally", '''
"""FastAPI dependency: the framework drives the generator to completion."""

import sqlite3

from fastapi import Depends, FastAPI

app = FastAPI()


def get_db():
    connection = sqlite3.connect("app.db")
    try:
        yield connection
    finally:
        connection.close()


@app.get("/people")
def list_people(db=Depends(get_db)):
    return [row[0] for row in db.execute("SELECT name FROM people")]
''')

add("frameworks", "atexit_register.py", ["EC-DEFER-01"], "A10: cleanup deferred to exit", '''
"""A process-lifetime log handle released by atexit."""

import atexit

AUDIT = open("audit.log", "a", encoding="utf-8")
atexit.register(AUDIT.close)


def record(message):
    AUDIT.write(message)
    AUDIT.flush()
''')

add("frameworks", "weakref_finalize.py", ["EC-DEFER-02"], "finalize ties cleanup to an owner", '''
"""Cleanup bound to the lifetime of the owning object."""

import socket
import weakref


class Probe:
    def __init__(self, host, port):
        sock = socket.create_connection((host, port))
        self._sock = sock
        weakref.finalize(self, sock.close)

    def ping(self):
        self._sock.sendall(b"ping")
''')

add("frameworks", "escape_to_caller.py", ["EC-ESC-01"], "A4: caller owns it, verdict UNKNOWN", '''
"""A factory: ownership transfers to the caller, so we cannot prove anything."""

import sqlite3


def open_store(path):
    return sqlite3.connect(path)  # leakguard: expect-unknown


def open_log(path):
    handle = open(path, "a", encoding="utf-8")  # leakguard: expect-unknown
    return handle
''')

add("frameworks", "handles_in_registry.py", ["EC-ESC-02"], "handles stored in a container", '''
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
''')


def main() -> int:
    samples: List[Sample] = []
    for index, (category, name, edge_cases, note, source) in enumerate(SAMPLES, start=1):
        abs_path = os.path.join(HANDWRITTEN, category, name)
        samples.append(
            build_sample(
                sample_id="R-%03d" % index,
                abs_path=abs_path,
                folder="real_code",
                origin="handwritten",
                family="real:%s:%s" % (category, name[:-3]),
                label=0,
                source=source,
                edge_cases=edge_cases,
                note=note,
            )
        )
    written = write_manifest(os.path.join(HANDWRITTEN, "manifest.jsonl"), samples)
    print("real_code/handwritten: %d samples" % written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
