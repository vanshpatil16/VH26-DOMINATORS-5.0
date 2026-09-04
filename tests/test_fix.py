import textwrap
from codegate.analyzer import analyze_source
from codegate.fix import fix_source, fix_source_validated

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


def test_fix_validation_line_shift_tolerant():
    """§27 regression: fixing a function with a close-removal shifts lines
    below it; validation must still accept fixes for subsequent functions."""
    src = textwrap.dedent("""
    def simple_leak(path):
        f = open(path, "r")
        data = f.read()
        return data

    def early_return(path, error):
        f = open(path, "r")
        if error:
            return "failed"
        data = f.read()
        f.close()
        return data

    def also_leaks(path):
        g = open(path, "r")
        return g.read()
    """)
    leaks = analyze_source(src, filename="t.py")
    result = fix_source_validated(src, leaks)
    assert result["applied"] is True
    assert result["rejected"] == [], f"all should fix, got rejections: {result['rejected']}"
    # all three functions now use `with`
    fixed = result["code"]
    assert fixed.count("with open") == 3
    # no definite leaks remain
    remaining = [lk for lk in analyze_source(fixed, filename="t.py")
                 if lk.confidence == "definite"]
    assert remaining == []


def test_fix_identity_based_not_line_based():
    """Regression: _WithFixer must locate the acquire by variable+API identity,
    not by line number (earlier fixes shift lines)."""
    src = textwrap.dedent("""
    def first(path):
        f = open(path)
        f.close()
        return 1

    def second(path):
        g = open(path)
        return g.read()
    """)
    leaks = analyze_source(src, filename="t.py")
    # first() is SAFE (closed on all paths); only second() leaks
    leak = next(lk for lk in leaks if lk.func == "second")
    assert leak.fixability == "safe"
    result = fix_source_validated(src, [lk for lk in leaks if lk.fixability == "safe"])
    assert result["applied"] is True
    fixed = result["code"]
    assert "with open(path) as g:" in fixed
    assert "with open(path) as f:" not in fixed  # first() untouched


def test_merge_duplicate_overwrite_finding():
    """§7/§19 regression: overwrite + exception on same var => ONE finding with
    stacked reasons, not two records."""
    src = textwrap.dedent("""
    def f(p1, p2):
        x = open(p1)
        x = open(p2)
        data = x.read()
        x.close()
        return data
    """)
    leaks = analyze_source(src, filename="t.py")
    overwrite = [lk for lk in leaks if lk.func == "f"]
    # exactly one finding, combining reassignment + exception escape
    assert len(overwrite) == 1, f"expected merged finding, got {len(overwrite)}"
    assert "reassignment" in overwrite[0].leak_reasons
    assert "exception escape" in overwrite[0].leak_reasons
