"""Duck-type fallback: unknown dotted APIs with an observed release call
are treated as resources (in-memory only, never persisted), reported at
`potential` confidence. No built-in rule, no user rule involved.
"""
import textwrap

from codegate.analyzer import analyze_source


def analyze(src, name="duck"):
    return analyze_source(textwrap.dedent(src), filename=name)


def path_leaks(src, name="duck"):
    return [lk for lk in analyze(src, name) if lk.kind in ("path", "path+exception")]


def test_duck_leak_is_potential():
    leaks = path_leaks(
        """\
        import vendordb
        def f():
            h = vendordb.connect("prod")
            x = h
            if not x:
                return None
            h.close()
            return x
        """,
        "duck_leak",
    )
    assert len(leaks) == 1
    assert leaks[0].confidence == "potential"
    assert leaks[0].severity == "warning"
    assert "inferred-resource" in leaks[0].leak_reasons


def test_duck_safe_quiet():
    assert (
        path_leaks(
            """\
            import vendordb
            def f():
                h = vendordb.connect("prod")
                x = h
                if not x:
                    h.close()
                    return None
                h.close()
                return x
            """,
            "duck_safe",
        )
        == []
    )


def test_duck_never_closed_silent():
    # No release observed anywhere -> not a resource, stay silent.
    assert (
        path_leaks(
            """\
            import vendordb
            def f():
                h = vendordb.connect("prod")
                return h.query("x")
            """,
            "duck_never_closed",
        )
        == []
    )


def test_duck_ignores_non_module_calls():
    # `session` is a local/param, not an imported module -> no inference.
    assert (
        path_leaks(
            """\
            def f(session):
                h = session.get("http://x")
                x = h
                if not x:
                    return None
                h.close()
                return x
            """,
            "duck_local",
        )
        == []
    )


def test_duck_lock_denylisted():
    # threading primitives are not OS resources even with release observed.
    assert (
        path_leaks(
            """\
            import threading
            def f(flag):
                lock = threading.Lock()
                lock.acquire()
                if flag:
                    lock.release()
                return 1
            """,
            "duck_lock",
        )
        == []
    )


def test_duck_quit_release():
    leaks = path_leaks(
        """\
        import vendordb
        def f():
            h = vendordb.connect("prod")
            x = h
            if not x:
                return None
            h.quit()
            return x
        """,
        "duck_quit",
    )
    assert len(leaks) == 1
    assert leaks[0].confidence == "potential"


def test_duck_with_acquire_silent():
    assert (
        path_leaks(
            """\
            import vendordb
            def f():
                with vendordb.connect("prod") as c:
                    return c.query("x")
            """,
            "duck_with",
        )
        == []
    )
