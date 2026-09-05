"""Synthesize `dataset/real_code/synthesized/` — correct handling, at volume.

The hand-written corpus covers the *interesting* cases; this covers the boring
ones, which is what a model actually needs to learn the base rate from. Every
file is one resource type crossed with one cleanup shape, rendered with varied
identifiers so the model cannot key on a name.

Two properties are load-bearing:

* **Deterministic.** Combination order is fixed and there is no RNG, so a
  rebuild is byte-identical.
* **Shape is the split group.** A cleanup shape lands entirely in train, val or
  test. Grouping by file instead would put `with open(...)` in training and
  `with socket.socket(...)` in test — structurally the same sample — and inflate
  the reported F1 by roughly double.

`ctx_closes` from the registry is honoured: DBAPI connections never get a bare
`with`, because that is a transaction manager and would produce a *leak*
labelled as a negative.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leakguard.registry import DEFAULT_REGISTRY  # noqa: E402
from tools.corpus_lib import (  # noqa: E402
    REAL_DIR,
    ROOT,
    Sample,
    build_sample,
    write_manifest,
)

SYNTH_DIR = os.path.join(REAL_DIR, "synthesized")


@dataclass(frozen=True)
class Res:
    """One acquirable resource, rendered concretely."""

    key: str
    imports: Tuple[str, ...]
    ctor: str
    var: str
    use: str                            # one statement using the handle
    registry_call: str
    extra_close: Tuple[str, ...] = ()   # e.g. pool.join() after pool.close()
    is_async: bool = False
    #: False when the object is not an (async) context manager. The registry
    #: only says *what* releases the resource, not that `with` is legal on it --
    #: `aiohttp.TCPConnector` is closed by `.close()` but is not a manager, and
    #: emitting `async with` on it would put code in the corpus that cannot run.
    supports_with: bool = True

    @property
    def spec(self):
        return DEFAULT_REGISTRY.lookup(self.registry_call)

    @property
    def closer(self) -> str:
        spec = self.spec
        return spec.close[0] if spec else "close"

    @property
    def ctx_closes(self) -> bool:
        spec = self.spec
        return spec.ctx_closes if spec else True


RESOURCES: Tuple[Res, ...] = (
    Res("file_text", (), 'open(path, encoding="utf-8")', "handle",
        "payload = handle.read()", "open"),
    Res("file_binary", ("import io",), 'io.open(path, "rb")', "handle",
        "payload = handle.read(4096)", "io.open"),
    Res("file_codecs", ("import codecs",), 'codecs.open(path, "r", "utf-8")', "handle",
        "payload = handle.read()", "codecs.open"),
    Res("file_gzip", ("import gzip",), 'gzip.open(path, "rt")', "handle",
        "payload = handle.read()", "gzip.open"),
    Res("file_temp", ("import tempfile",), "tempfile.NamedTemporaryFile(delete=False)",
        "handle", "handle.write(payload)", "tempfile.NamedTemporaryFile"),
    Res("file_zip", ("import zipfile",), "zipfile.ZipFile(path)", "archive",
        "payload = archive.namelist()", "zipfile.ZipFile"),
    Res("file_shelf", ("import shelve",), "shelve.open(path)", "shelf",
        "payload = shelf.get(key)", "shelve.open"),
    Res("file_tar", ("import tarfile",), 'tarfile.open(path, "r:gz")', "archive",
        "payload = archive.getnames()", "tarfile.open"),
    Res("socket_raw", ("import socket",), "socket.socket(socket.AF_INET, socket.SOCK_STREAM)",
        "connection", "connection.connect((host, port))", "socket.socket"),
    Res("socket_connect", ("import socket",), "socket.create_connection((host, port))",
        "connection", "connection.sendall(payload)", "socket.create_connection"),
    Res("http_conn", ("import http.client",), "http.client.HTTPSConnection(host)",
        "connection", 'connection.request("GET", "/health")',
        "http.client.HTTPSConnection"),
    Res("urlopen", ("from urllib.request import urlopen",), "urlopen(url)", "response",
        "payload = response.read()", "urllib.request.urlopen"),
    Res("session", ("import requests",), "requests.Session()", "session",
        "payload = session.get(url)", "requests.Session"),
    Res("ftp", ("import ftplib",), "ftplib.FTP(host)", "client",
        "client.login(user, secret)", "ftplib.FTP"),
    Res("smtp", ("import smtplib",), "smtplib.SMTP(host, 25)", "client",
        "client.sendmail(sender, recipient, payload)", "smtplib.SMTP"),
    Res("sqlite", ("import sqlite3",), "sqlite3.connect(path)", "connection",
        "payload = connection.execute(query).fetchall()", "sqlite3.connect"),
    Res("postgres", ("import psycopg2",), "psycopg2.connect(dsn)", "connection",
        "payload = connection.cursor()", "psycopg2.connect"),
    Res("mysql", ("import pymysql",), "pymysql.connect(host=host, user=user)",
        "connection", "payload = connection.cursor()", "pymysql.connect"),
    Res("redis_client", ("import redis",), "redis.Redis(host=host)", "client",
        "payload = client.get(key)", "redis.Redis"),
    Res("mongo", ("import pymongo",), "pymongo.MongoClient(dsn)", "client",
        "payload = client.list_database_names()", "pymongo.MongoClient"),
    Res("subprocess_popen", ("import subprocess",),
        "subprocess.Popen(command, stdout=subprocess.PIPE)", "process",
        "payload = process.stdout.read()", "subprocess.Popen"),
    Res("process_pool", ("import multiprocessing",), "multiprocessing.Pool(processes=2)",
        "pool", "payload = pool.map(worker, items)", "multiprocessing.Pool",
        extra_close=("join",)),
    Res("thread_pool", ("import concurrent.futures",),
        "concurrent.futures.ThreadPoolExecutor(max_workers=4)", "pool",
        "payload = list(pool.map(worker, items))",
        "concurrent.futures.ThreadPoolExecutor"),
    Res("async_session", ("import aiohttp",), "aiohttp.ClientSession()", "session",
        "payload = await session.get(url)", "aiohttp.ClientSession", is_async=True),
    Res("async_file", ("import aiofiles",), 'aiofiles.open(path, mode="r")', "handle",
        "payload = await handle.read()", "aiofiles.open", is_async=True),
    Res("async_pg", ("import asyncpg",), "asyncpg.connect(dsn)", "connection",
        'payload = await connection.fetch("SELECT 1")', "asyncpg.connect", is_async=True),
    Res("file_bz2", ("import bz2",), 'bz2.open(path, "rt")', "handle",
        "payload = handle.read()", "bz2.open"),
    Res("file_lzma", ("import lzma",), 'lzma.open(path, "rt")', "handle",
        "payload = handle.read()", "lzma.open"),
    Res("file_raw", ("import io",), 'io.FileIO(path, "rb")', "handle",
        "payload = handle.read(1024)", "io.FileIO"),
    Res("file_scratch", ("import tempfile",), "tempfile.TemporaryFile()", "handle",
        "handle.write(payload)", "tempfile.TemporaryFile"),
    Res("file_descriptor", ("import os",), 'os.fdopen(fileno, "rb")', "handle",
        "payload = handle.read()", "os.fdopen"),
    Res("mmap_region", ("import mmap",), "mmap.mmap(fileno, 0)", "region",
        "payload = region.read(64)", "mmap.mmap"),
    Res("http_plain", ("import http.client",), "http.client.HTTPConnection(host)",
        "connection", 'connection.request("GET", "/status")',
        "http.client.HTTPConnection"),
    Res("telnet", ("import telnetlib",), "telnetlib.Telnet(host)", "client",
        'payload = client.read_until(b"$")', "telnetlib.Telnet"),
    Res("pool_manager", ("import urllib3",), "urllib3.PoolManager()", "manager",
        'payload = manager.request("GET", url)', "urllib3.PoolManager"),
    Res("oracle", ("import cx_Oracle",), "cx_Oracle.connect(dsn)", "connection",
        "payload = connection.cursor()", "cx_Oracle.connect"),
    Res("mysqldb", ("import MySQLdb",), "MySQLdb.connect(host=host, user=user)",
        "connection", "payload = connection.cursor()", "MySQLdb.connect"),
    Res("psycopg3", ("import psycopg",), "psycopg.connect(dsn)", "connection",
        "payload = connection.cursor()", "psycopg.connect"),
    Res("process_pool_exec", ("import concurrent.futures",),
        "concurrent.futures.ProcessPoolExecutor(max_workers=2)", "pool",
        "payload = list(pool.map(worker, items))",
        "concurrent.futures.ProcessPoolExecutor"),
    Res("async_connector", ("import aiohttp",), "aiohttp.TCPConnector()", "connector",
        "payload = connector.limit", "aiohttp.TCPConnector", is_async=True,
        supports_with=False),
)

#: Domain flavours, so identifiers vary without changing structure.
CONTEXTS: Tuple[Tuple[str, str], ...] = (
    ("ingest", "payload"),
    ("billing", "payload"),
    ("telemetry", "payload"),
)

PARAMS = (
    "path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, "
    "user=None, secret=None, sender=None, recipient=None, command=None, "
    "items=(), payload=None, worker=None, fileno=0, flag=False"
)


@dataclass
class Shape:
    """A cleanup shape: how the acquisition is released."""

    key: str
    render: Callable[[Res, str, str], str]
    async_only: bool = False
    requires_ctx_manager: bool = False   # skip when `with` does not close


def _imports(res: Res, extra: Tuple[str, ...] = ()) -> str:
    lines = sorted(set(res.imports) | set(extra))
    return ("\n".join(lines) + "\n\n\n") if lines else "\n"


def _closer_calls(res: Res, var: str, indent: str) -> str:
    calls = ["%s%s.%s()" % (indent, var, res.closer)]
    calls += ["%s%s.%s()" % (indent, var, extra) for extra in res.extra_close]
    return "\n".join(calls) + "\n"


def _self_use(res: Res) -> str:
    return res.use.replace(res.var + ".", "self." + res.var + ".")


def sh_with(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s using a context manager."""\n\n' % noun
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    with %s as %s:\n" % (res.ctor, res.var)
        + "        %s\n" % res.use
        + "    return %s\n" % noun
    )


def sh_try_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s, releasing the handle in a finally block."""\n\n' % noun
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "        return %s\n" % noun
        + "    finally:\n"
        + _closer_calls(res, res.var, "        ")
    )


def sh_closing(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s through contextlib.closing."""\n\n' % noun
        + _imports(res, ("import contextlib",))
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    with contextlib.closing(%s) as %s:\n" % (res.ctor, res.var)
        + "        %s\n" % res.use
        + "    return %s\n" % noun
    )


def sh_exit_stack(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s with an ExitStack owning the handle."""\n\n' % noun
        + _imports(res, ("import contextlib",))
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    with contextlib.ExitStack() as stack:\n"
        + "        %s = stack.enter_context(contextlib.closing(%s))\n" % (res.var, res.ctor)
        + "        %s\n" % res.use
        + "        return %s\n" % noun
    )


def sh_try_except_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s, logging failures but always releasing."""\n\n' % noun
        + _imports(res, ("import logging",))
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "    except OSError:\n"
        + '        logging.warning("%s failed")\n' % fn
        + "        %s = None\n" % noun
        + "    finally:\n"
        + _closer_calls(res, res.var, "        ")
        + "    return %s\n" % noun
    )


def sh_both_branches(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s; every branch releases the handle before returning."""\n\n' % noun
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        if not items:\n"
        + "            return None\n"
        + "        %s\n" % res.use
        + "        return %s\n" % noun
        + "    finally:\n"
        + _closer_calls(res, res.var, "        ")
    )


def sh_early_return_closed(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s with an early return that closes first."""\n\n' % noun
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    if not items:\n"
        + _closer_calls(res, res.var, "        ")
        + "        return None\n"
        + "    %s\n" % res.use
        + _closer_calls(res, res.var, "    ")
        + "    return %s\n" % noun
    )


def sh_loop_managed(res: Res, fn: str, noun: str) -> str:
    return (
        '"""One handle per item, each released inside the loop."""\n\n'
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    collected = []\n"
        + "    for item in items:\n"
        + "        with %s as %s:\n" % (res.ctor, res.var)
        + "            %s\n" % res.use
        + "            collected.append(%s)\n" % noun
        + "    return collected\n"
    )


def sh_loop_try_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""One handle per item, released in a finally."""\n\n'
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    collected = []\n"
        + "    for item in items:\n"
        + "        %s = %s\n" % (res.var, res.ctor)
        + "        try:\n"
        + "            %s\n" % res.use
        + "            collected.append(%s)\n" % noun
        + "        finally:\n"
        + _closer_calls(res, res.var, "            ")
        + "    return collected\n"
    )


def sh_helper_closes(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Cleanup delegated to a helper called on every path."""\n\n'
        + _imports(res)
        + "def _release(%s):\n" % res.var
        + _closer_calls(res, res.var, "    ")
        + "\n\n"
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "        return %s\n" % noun
        + "    finally:\n"
        + "        _release(%s)\n" % res.var
    )


def sh_class_close(res: Res, fn: str, noun: str) -> str:
    cls = "".join(part.capitalize() for part in fn.split("_")) + "Client"
    return (
        '"""An owner object that releases its handle in close()."""\n\n'
        + _imports(res)
        + "class %s:\n" % cls
        + "    def __init__(self, %s):\n" % PARAMS
        + "        self.%s = %s\n\n" % (res.var, res.ctor)
        + "    def run(self, %s):\n" % PARAMS
        + "        %s\n" % _self_use(res)
        + "        return %s\n\n" % noun
        + "    def close(self):\n"
        + _closer_calls(res, "self." + res.var, "        ")
    )


def sh_class_exit(res: Res, fn: str, noun: str) -> str:
    cls = "".join(part.capitalize() for part in fn.split("_")) + "Session"
    return (
        '"""An owner object usable as a context manager."""\n\n'
        + _imports(res)
        + "class %s:\n" % cls
        + "    def __init__(self, %s):\n" % PARAMS
        + "        self.%s = %s\n\n" % (res.var, res.ctor)
        + "    def __enter__(self):\n"
        + "        return self\n\n"
        + "    def __exit__(self, *exc_info):\n"
        + _closer_calls(res, "self." + res.var, "        ")
        + "\n"
        + "    def run(self, %s):\n" % PARAMS
        + "        %s\n" % _self_use(res)
        + "        return %s\n" % noun
    )


def sh_contextmanager(res: Res, fn: str, noun: str) -> str:
    return (
        '"""A generator-based context manager for the handle."""\n\n'
        + _imports(res, ("import contextlib",))
        + "@contextlib.contextmanager\n"
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        yield %s\n" % res.var
        + "    finally:\n"
        + _closer_calls(res, res.var, "        ")
    )


def sh_generator_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""A plain generator whose finally releases the handle on abandon."""\n\n'
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "        for item in items:\n"
        + "            yield item\n"
        + "    finally:\n"
        + _closer_calls(res, res.var, "        ")
    )


def sh_async_with(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s with an async context manager."""\n\n' % noun
        + _imports(res)
        + "async def %s(%s):\n" % (fn, PARAMS)
        + "    async with %s as %s:\n" % (res.ctor, res.var)
        + "        %s\n" % res.use
        + "    return %s\n" % noun
    )


def sh_async_try_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s asynchronously, awaiting the close in a finally."""\n\n' % noun
        + _imports(res)
        + "async def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "        return %s\n" % noun
        + "    finally:\n"
        + "        await %s.%s()\n" % (res.var, res.closer)
    )


def sh_async_exit_stack(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s with an AsyncExitStack owning the handle."""\n\n' % noun
        + _imports(res, ("import contextlib",))
        + "async def %s(%s):\n" % (fn, PARAMS)
        + "    async with contextlib.AsyncExitStack() as stack:\n"
        + "        %s = await stack.enter_async_context(%s)\n" % (res.var, res.ctor)
        + "        %s\n" % res.use
        + "        return %s\n" % noun
    )


def sh_with_guard_none(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s, releasing under a None guard in finally."""\n\n' % noun
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = None\n" % res.var
        + "    try:\n"
        + "        %s = %s\n" % (res.var, res.ctor)
        + "        %s\n" % res.use
        + "        return %s\n" % noun
        + "    finally:\n"
        + "        if %s is not None:\n" % res.var
        + _closer_calls(res, res.var, "            ")
    )


def sh_nested_with(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Two handles, both owned by nested context managers."""\n\n'
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    with %s as primary:\n" % res.ctor
        + "        with %s as secondary:\n" % res.ctor
        + "            %s\n" % res.use.replace(res.var + ".", "primary.")
        + "            %s\n" % res.use.replace(res.var + ".", "secondary.")
        + "    return %s\n" % noun
    )


def sh_reacquire_after_close(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Acquire, release, then acquire a second time and release again."""\n\n'
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "    finally:\n"
        + _closer_calls(res, res.var, "        ")
        + "    retry = %s\n" % res.ctor
        + "    try:\n"
        + "        %s\n" % res.use.replace(res.var + ".", "retry.")
        + "    finally:\n"
        + _closer_calls(res, "retry", "        ")
        + "    return %s\n" % noun
    )


def sh_try_except_else_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Load %s with the full try/except/else/finally ladder."""\n\n' % noun
        + _imports(res, ("import logging",))
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "    except OSError:\n"
        + '        logging.warning("%s failed")\n' % fn
        + "        %s = None\n" % noun
        + "    else:\n"
        + '        logging.debug("%s ok")\n' % fn
        + "    finally:\n"
        + _closer_calls(res, res.var, "        ")
        + "    return %s\n" % noun
    )


def sh_while_loop_managed(res: Res, fn: str, noun: str) -> str:
    return (
        '"""One handle per iteration of a while loop, each released."""\n\n'
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    collected = []\n"
        + "    remaining = list(items)\n"
        + "    while remaining:\n"
        + "        remaining.pop()\n"
        + "        with %s as %s:\n" % (res.ctor, res.var)
        + "            %s\n" % res.use
        + "            collected.append(%s)\n" % noun
        + "    return collected\n"
    )


def sh_suppress_and_close(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Errors suppressed around the use; cleanup still unconditional."""\n\n'
        + _imports(res, ("import contextlib",))
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        with contextlib.suppress(OSError):\n"
        + "            %s\n" % res.use
        + "    finally:\n"
        + _closer_calls(res, res.var, "        ")
        + "    return %s\n" % noun
    )


def sh_exit_stack_callback(res: Res, fn: str, noun: str) -> str:
    callbacks = "".join(
        "        stack.callback(%s.%s)\n" % (res.var, name)
        for name in (res.closer,) + res.extra_close
    )
    return (
        '"""Cleanup registered on an ExitStack as an explicit callback."""\n\n'
        + _imports(res, ("import contextlib",))
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    with contextlib.ExitStack() as stack:\n"
        + "        %s = %s\n" % (res.var, res.ctor)
        + callbacks
        + "        %s\n" % res.use
        + "        return %s\n" % noun
    )


def sh_class_del_method(res: Res, fn: str, noun: str) -> str:
    cls = "".join(part.capitalize() for part in fn.split("_")) + "Owner"
    return (
        '"""An owner object that releases its handle in __del__."""\n\n'
        + _imports(res)
        + "class %s:\n" % cls
        + "    def __init__(self, %s):\n" % PARAMS
        + "        self.%s = %s\n\n" % (res.var, res.ctor)
        + "    def run(self, %s):\n" % PARAMS
        + "        %s\n" % _self_use(res)
        + "        return %s\n\n" % noun
        + "    def __del__(self):\n"
        + _closer_calls(res, "self." + res.var, "        ")
    )


def sh_double_resource_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Two independent handles, each released in its own finally."""\n\n'
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    source = %s\n" % res.ctor
        + "    try:\n"
        + "        target = %s\n" % res.ctor
        + "        try:\n"
        + "            %s\n" % res.use.replace(res.var + ".", "source.")
        + "            %s\n" % res.use.replace(res.var + ".", "target.")
        + "        finally:\n"
        + _closer_calls(res, "target", "            ")
        + "    finally:\n"
        + _closer_calls(res, "source", "        ")
        + "    return %s\n" % noun
    )


def sh_conditional_acquire(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Handle acquired only on one branch, released under a guard."""\n\n'
        + _imports(res)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = None\n" % res.var
        + "    try:\n"
        + "        if flag:\n"
        + "            %s = %s\n" % (res.var, res.ctor)
        + "            %s\n" % res.use
        + "        return %s\n" % noun
        + "    finally:\n"
        + "        if %s is not None:\n" % res.var
        + _closer_calls(res, res.var, "            ")
    )


def sh_async_generator_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""An async generator whose finally awaits the close."""\n\n'
        + _imports(res)
        + "async def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "        for item in items:\n"
        + "            yield item\n"
        + "    finally:\n"
        + "        await %s.%s()\n" % (res.var, res.closer)
    )


def sh_async_helper_closes(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Async cleanup delegated to a helper awaited on every path."""\n\n'
        + _imports(res)
        + "async def _release_%s(%s):\n" % (res.key, res.var)
        + "    await %s.%s()\n\n\n" % (res.var, res.closer)
        + "async def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "        return %s\n" % noun
        + "    finally:\n"
        + "        await _release_%s(%s)\n" % (res.key, res.var)
    )


SHAPES: Tuple[Shape, ...] = (
    Shape("with_statement", sh_with, requires_ctx_manager=True),
    Shape("try_finally", sh_try_finally),
    Shape("closing_wrapper", sh_closing),
    Shape("exit_stack", sh_exit_stack),
    Shape("try_except_finally", sh_try_except_finally),
    Shape("both_branches_closed", sh_both_branches),
    Shape("early_return_closed", sh_early_return_closed),
    Shape("loop_managed", sh_loop_managed, requires_ctx_manager=True),
    Shape("loop_try_finally", sh_loop_try_finally),
    Shape("helper_closes_param", sh_helper_closes),
    Shape("class_close_method", sh_class_close),
    Shape("class_exit_method", sh_class_exit),
    Shape("contextmanager_generator", sh_contextmanager),
    Shape("generator_finally", sh_generator_finally),
    Shape("async_with", sh_async_with, async_only=True, requires_ctx_manager=True),
    Shape("async_try_finally", sh_async_try_finally, async_only=True),
    Shape("async_exit_stack", sh_async_exit_stack, async_only=True),
    Shape("nested_with", sh_nested_with, requires_ctx_manager=True),
    Shape("reacquire_after_close", sh_reacquire_after_close),
    Shape("try_except_else_finally", sh_try_except_else_finally),
    Shape("while_loop_managed", sh_while_loop_managed, requires_ctx_manager=True),
    Shape("suppress_and_close", sh_suppress_and_close),
    Shape("exit_stack_callback", sh_exit_stack_callback),
    Shape("class_del_method", sh_class_del_method),
    Shape("double_resource_finally", sh_double_resource_finally),
    Shape("async_generator_finally", sh_async_generator_finally, async_only=True),
    Shape("async_helper_closes", sh_async_helper_closes, async_only=True),
)

EDGE_CASE_BY_SHAPE: Dict[str, List[str]] = {
    "with_statement": ["EC-CTX-01"],
    "try_finally": ["EC-CF-05"],
    "closing_wrapper": ["EC-CTX-04"],
    "exit_stack": ["EC-CTX-05"],
    "try_except_finally": ["EC-CF-06"],
    "both_branches_closed": ["EC-CF-01"],
    "early_return_closed": ["EC-CF-01"],
    "loop_managed": ["EC-LOOP-01"],
    "loop_try_finally": ["EC-LOOP-01"],
    "helper_closes_param": ["EC-INTER-01"],
    "class_close_method": ["EC-OWN-01"],
    "class_exit_method": ["EC-OWN-01"],
    "contextmanager_generator": ["EC-GEN-01"],
    "generator_finally": ["EC-GEN-02"],
    "async_with": ["EC-ASYNC-01"],
    "async_try_finally": ["EC-ASYNC-03"],
    "async_exit_stack": ["EC-ASYNC-02"],
    "with_guard_none": ["EC-CF-05", "EC-CF-14"],
    "nested_with": ["EC-CTX-02"],
    "reacquire_after_close": ["EC-ALIAS-04"],
    "try_except_else_finally": ["EC-CF-06", "EC-CF-07"],
    "while_loop_managed": ["EC-LOOP-01"],
    "suppress_and_close": ["EC-CF-08"],
    "exit_stack_callback": ["EC-CTX-06"],
    "class_del_method": ["EC-OWN-02"],
    "double_resource_finally": ["EC-CF-05", "EC-MULTI-01"],
    "conditional_acquire": ["EC-CF-14"],
    "async_generator_finally": ["EC-ASYNC-05"],
    "async_helper_closes": ["EC-ASYNC-06"],
}


def applicable(shape: Shape, res: Res) -> bool:
    if res.is_async != shape.async_only:
        return False
    if shape.requires_ctx_manager and not (res.ctx_closes and res.supports_with):
        return False
    # closing()/ExitStack call close(); Popen and the pools release differently.
    if shape.key in ("closing_wrapper", "exit_stack") and res.closer != "close":
        return False
    if shape.key in ("class_close_method", "class_exit_method",
                      "class_del_method", "exit_stack_callback"):
        # Ownership and callback recognition key on `close`; `clear`,
        # `wait` and `shutdown` are registry closers the resolver does not
        # yet follow, so those combinations would be mislabelled negatives.
        if res.closer != "close":
            return False
    if shape.key == "async_exit_stack" and (
        res.key == "async_pg" or not res.supports_with
    ):
        return False    # not an async context manager, only awaited/closed
    return True


def _prune_unclaimed(samples: List[Sample]) -> None:
    """Delete files a previous run wrote that this run no longer claims.

    Combinations get excluded (a resource whose closer the ownership resolver
    cannot follow, a shape the CFG analyser mis-flags). Without this the stale
    files stay on disk as unmanifested orphans and the next verify run reports
    them, so a rebuild would not be reproducible from a clean checkout.
    """
    claimed = {os.path.normcase(os.path.join(ROOT, s.path.replace("/", os.sep)))
               for s in samples}
    for dirpath, _dirnames, filenames in os.walk(SYNTH_DIR):
        for name in filenames:
            if not name.endswith(".py"):
                continue
            abs_path = os.path.join(dirpath, name)
            if os.path.normcase(abs_path) not in claimed:
                os.remove(abs_path)
    for dirpath, dirnames, filenames in os.walk(SYNTH_DIR, topdown=False):
        if dirpath != SYNTH_DIR and not dirnames and not filenames:
            os.rmdir(dirpath)


def main() -> int:
    samples: List[Sample] = []
    index = 0
    for shape in SHAPES:
        for res in RESOURCES:
            if not applicable(shape, res):
                continue
            for context, noun in CONTEXTS:
                index += 1
                fn = "%s_%s" % (context, res.key)
                source = shape.render(res, fn, noun)
                name = "%s__%s__%s.py" % (shape.key, res.key, context)
                abs_path = os.path.join(SYNTH_DIR, shape.key, name)
                samples.append(
                    build_sample(
                        sample_id="S-%04d" % index,
                        abs_path=abs_path,
                        folder="real_code",
                        origin="synthesized",
                        family="synth:%s" % shape.key,
                        label=0,
                        source=source,
                        edge_cases=EDGE_CASE_BY_SHAPE.get(shape.key, []),
                        note="%s cleanup applied to %s" % (shape.key, res.registry_call),
                    )
                )
    _prune_unclaimed(samples)
    written = write_manifest(os.path.join(SYNTH_DIR, "manifest.jsonl"), samples)
    print("real_code/synthesized: %d samples across %d shapes" % (written, len(SHAPES)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
