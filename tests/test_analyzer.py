import textwrap
from codegate.analyzer import analyze_source

CFG = __import__('codegate.config', fromlist=['CodeGateConfig']).CodeGateConfig.default

def check(src, expect_leak, name="test"):
    """Check for PATH leaks (normal control-flow). Exception-only findings are
    covered in tests/test_hardened.py — a path-safe but exception-unsafe acquire
    is intentional HARDEN-3 behavior, so we filter to kind='path' here."""
    leaks = analyze_source(textwrap.dedent(src), filename=name)
    path_leaks = [lk for lk in leaks if lk.kind in ("path", "path+exception")]
    got = len(path_leaks) > 0
    assert got == expect_leak, f"{name}: expect_leak={expect_leak} got={got} path_leaks={[l.message for l in path_leaks]} all={[(l.kind, l.acquire_line) for l in leaks]}"

def test_leak_simple():
    check("""
    def leak(path):
        f = open(path)
        data = f.read()
        if not data:
            return None
        f.close()
        return data
    """, True, "leak_simple")

def test_safe_both():
    check("""
    def safe(path):
        f = open(path)
        data = f.read()
        if not data:
            f.close()
            return None
        f.close()
        return data
    """, False)

def test_with_safe():
    check("""
    def foo(path):
        with open(path) as f:
            data = f.read()
        return data
    """, False)

def test_alias_safe():
    check("""
    def foo(path):
        f = open(path)
        g = f
        g.close()
        return 1
    """, False)

def test_alias_leak_branch():
    check("""
    def foo(path):
        f = open(path)
        g = f
        if True:
            g.close()
        return 1
    """, True)

def test_return_transfer():
    check("""
    def factory(path):
        f = open(path)
        return f
    """, False)

def test_reassign_leak():
    check("""
    def foo(path):
        f = open(path)
        f = open(path)
        f.close()
        return 1
    """, True)

def test_loop_safe():
    check("""
    def foo(path):
        f = open(path)
        for i in range(3):
            print(i)
        f.close()
        return 1
    """, False)

def test_loop_branch_leak():
    check("""
    def foo(path):
        f = open(path)
        if True:
            f.close()
        return 1
    """, True)

def test_try_finally_safe():
    check("""
    def foo(path):
        f = open(path)
        try:
            data = f.read()
            return data
        finally:
            f.close()
    """, False)

def test_try_except_without_finally_leak():
    # This is try/except without finally + close after -> if exception, close not reached?
    # Scalpel's patched CFG still models it, but we treat as potential leak if exception path doesn't close
    # For MVP, we check that our analyzer doesn't crash
    src = """
    def foo(path):
        f = open(path)
        try:
            data = f.read()
        except:
            data = None
        f.close()
        return data
    """
    leaks = analyze_source(textwrap.dedent(src), filename="try_except")
    # This may be safe or leak depending on exception CFG modeling; just ensure no crash and returns list
    assert isinstance(leaks, list)

def test_nested_if():
    check("""
    def foo(x, y, path):
        f = open(path)
        if x:
            if y:
                f.close()
                return 1
            return 2
        f.close()
        return 3
    """, True)

def test_socket():
    check("""
    def foo():
        import socket
        s = socket.socket()
        s.close()
        return 1
    """, False)

if __name__ == "__main__":
    test_leak_simple(); print("leak_simple ok")
    test_safe_both(); print("safe_both ok")
    test_with_safe(); print("with_safe ok")
    test_alias_safe(); print("alias_safe ok")
    test_alias_leak_branch(); print("alias_leak_branch ok")
    test_return_transfer(); print("return_transfer ok")
    test_reassign_leak(); print("reassign ok")
    test_loop_safe(); print("loop_safe ok")
    test_loop_branch_leak(); print("loop_branch_leak ok")
    test_try_finally_safe(); print("try_finally ok")
    test_try_except_without_finally_leak(); print("try_except ok")
    test_nested_if(); print("nested_if ok")
    test_socket(); print("socket ok")
    print("All pass")
