"""CodeGate benchmark corpus — labeled resource-leak cases.

Each case: name, source (a single function), expected label:
  "leak"         -> a definite leak is expected
  "safe"         -> no leak expected
  "potential"    -> ownership/unknown semantics; definite is not required
"""

import textwrap

CASES = [
    {
        "name": "simple_leak",
        "expected": "leak",
        "source": textwrap.dedent("""\
            def simple_leak(path):
                f = open(path, "r")
                data = f.read()
                return data
            """),
    },
    {
        "name": "early_return",
        "expected": "leak",
        "source": textwrap.dedent("""\
            def early_return(path, error):
                f = open(path, "r")
                if error:
                    return "failed"
                data = f.read()
                f.close()
                return data
            """),
    },
    {
        "name": "loop_leak",
        "expected": "leak",
        "source": textwrap.dedent("""\
            def loop_leak(files):
                results = []
                for path in files:
                    f = open(path, "r")
                    results.append(f.read())
                    if len(results) > 10:
                        return results
                    f.close()
                return results
            """),
    },
    {
        "name": "exception_leak",
        "expected": "leak",
        "source": textwrap.dedent("""\
            def exception_leak(path):
                f = open(path, "r")
                try:
                    process_file(f)
                except Exception:
                    return None
                f.close()
            """),
    },
    {
        "name": "nested_exception_leak",
        "expected": "leak",
        "source": textwrap.dedent("""\
            def nested_exception_leak(path):
                f = open(path, "r")
                try:
                    process_file(f)
                except Exception:
                    log_error()
                f.close()
            """),
    },
    {
        "name": "multiple_resources",
        "expected": "leak",
        "source": textwrap.dedent("""\
            def multiple_resources(path1, path2):
                f1 = open(path1, "r")
                f2 = open(path2, "r")
                try:
                    data1 = f1.read()
                    data2 = f2.read()
                    if not data1:
                        return data2
                except Exception:
                    f1.close()
                    return None
                f1.close()
                return data1 + data2
            """),
    },
    {
        "name": "overwritten_resource",
        "expected": "leak",
        "source": textwrap.dedent("""\
            def overwritten_resource(path1, path2):
                f = open(path1, "r")
                f = open(path2, "r")
                data = f.read()
                f.close()
                return data
            """),
    },
    {
        "name": "caller_interproc",
        "expected": "leak",  # local callee proven to leak on one path
        "source": textwrap.dedent("""\
            def caller(path):
                f = open(path, "r")
                process_and_maybe_close(f)
                return "done"

            def process_and_maybe_close(f):
                data = f.read()
                if "SECRET" in data:
                    return data
                f.close()
                return data
            """),
    },
    {
        "name": "socket_leak",
        "expected": "leak",
        "source": textwrap.dedent("""\
            import socket
            def socket_leak():
                s = socket.socket()
                s.connect(("example.com", 80))
                if some_condition():
                    return "failed"
                s.close()
                return "done"
            """),
    },
    {
        "name": "database_leak",
        "expected": "leak",
        "source": textwrap.dedent("""\
            import sqlite3
            def database_leak(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                if some_condition():
                    return None
                cursor.execute("SELECT * FROM users")
                conn.close()
                return "done"
            """),
    },
    {
        "name": "safe_explicit",
        "expected": "safe",
        "source": textwrap.dedent("""\
            def safe_explicit(path):
                f = open(path, "r")
                try:
                    return f.read()
                finally:
                    f.close()
            """),
    },
    {
        "name": "safe_with",
        "expected": "safe",
        "source": textwrap.dedent("""\
            def safe_with(path):
                with open(path, "r") as f:
                    return f.read()
            """),
    },
    {
        "name": "safe_multiple",
        "expected": "safe",
        "source": textwrap.dedent("""\
            def safe_multiple(path1, path2):
                with open(path1, "r") as f1:
                    with open(path2, "r") as f2:
                        return f1.read() + f2.read()
            """),
    },
    {
        "name": "safe_loop",
        "expected": "safe",
        "source": textwrap.dedent("""\
            def safe_loop(files):
                results = []
                for path in files:
                    with open(path, "r") as f:
                        results.append(f.read())
                return results
            """),
    },
    {
        "name": "nightmare",
        "expected": "leak",
        "source": textwrap.dedent("""\
            def nightmare(files, should_stop):
                for path in files:
                    f = open(path, "r")
                    try:
                        data = f.read()
                        if should_stop(data):
                            return data
                        if not data:
                            continue
                        process_file(f)
                    except Exception:
                        handle_error()
                    if should_close(data):
                        f.close()
                return None
            """),
    },
    {
        "name": "safe_alias",
        "expected": "safe",
        "source": textwrap.dedent("""\
            def safe_alias(path):
                f = open(path)
                g = f
                g.close()
                return 1
            """),
    },
    {
        "name": "safe_try_finally_return",
        "expected": "safe",
        "source": textwrap.dedent("""\
            def safe_try_finally_return(path):
                f = open(path)
                try:
                    return f.read()
                finally:
                    f.close()
            """),
    },
    {
        "name": "returned_resource",
        "expected": "potential",  # ownership transfer — not an automatic definite leak
        "source": textwrap.dedent("""\
            def returned_resource(path):
                f = open(path)
                return f
            """),
    },
    {
        "name": "second_open_raises",
        # §2: if the SECOND acquisition raises, f1 is OPEN and never closed —
        # f1 leaks on that exceptional path (f2 is NOT_ACQUIRED, no leak for f2).
        "expected": "leak",
        "source": textwrap.dedent("""\
            def second_open_raises(path1, path2):
                f1 = open(path1)
                f2 = open(path2)
                f1.close()
                f2.close()
                return 1
            """),
    },
]


def corpus() -> list[dict]:
    return [dict(c) for c in CASES]