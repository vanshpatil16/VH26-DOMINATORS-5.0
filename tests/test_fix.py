import textwrap
from codegate.analyzer import analyze_source
from codegate.fix import fix_source

def test_fix_preserves_comment():
    src = textwrap.dedent("""
    def read_file(path):
        f = open(path)

        # important comment
        data = f.read()

        if not data:
            return None

        f.close()
        return data
    """)
    leaks = analyze_source(src, filename="test.py")
    assert len(leaks) == 1
    fixed = fix_source(src, leaks)
    assert "with open(path) as f:" in fixed
    assert "# important comment" in fixed
    assert "f.close()" not in fixed
    # Fixed should not leak
    assert len(analyze_source(fixed, filename="test.py")) == 0

def test_fix_with_leak_simple():
    src = textwrap.dedent("""
    def leak(path):
        f = open(path)
        data = f.read()
        if not data:
            return None
        f.close()
        return data
    """)
    leaks = analyze_source(src, filename="t.py")
    fixed = fix_source(src, leaks)
    assert len(analyze_source(fixed, filename="t.py")) == 0

def test_fix_no_change_when_safe():
    src = textwrap.dedent("""
    def safe(path):
        with open(path) as f:
            data = f.read()
        return data
    """)
    leaks = analyze_source(src, filename="t.py")
    assert len(leaks) == 0
    assert fix_source(src, leaks) == src

if __name__ == "__main__":
    test_fix_preserves_comment(); print("fix comment ok")
    test_fix_with_leak_simple(); print("fix leak ok")
    test_fix_no_change_when_safe(); print("fix safe ok")
    print("all fix tests pass")
