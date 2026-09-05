"""Stdlib high-frequency resource rules (batch 1).

Each rule has a LEAK test (must flag) and a SAFE test (must stay quiet).
Regression pair at the bottom covers APIs already handled without new specs.
"""
import textwrap

from codegate.analyzer import analyze_source


def check(src, expect_leak, name):
    """Path-leak check (same semantics as tests/test_analyzer.py)."""
    leaks = analyze_source(textwrap.dedent(src), filename=name)
    path_leaks = [lk for lk in leaks if lk.kind in ("path", "path+exception")]
    got = len(path_leaks) > 0
    assert got == expect_leak, (
        f"{name}: expect_leak={expect_leak} got={got} "
        f"path={[l.message for l in path_leaks]} "
        f"all={[(l.kind, l.acquire_line) for l in leaks]}"
    )


def leak_shape(acquire):
    return f"""
    def f():
        h = {acquire}
        x = h
        if not x:
            return None
        h.close()
        return x
    """


def safe_shape(acquire, release="h.close()"):
    return f"""
    def f():
        h = {acquire}
        x = h
        if not x:
            {release}
            return None
        {release}
        return x
    """


# ── os.fdopen (fd -> file object, method release) ──
def test_os_fdopen_leak():
    check(leak_shape("os.fdopen(1)"), True, "os_fdopen_leak")


def test_os_fdopen_safe():
    check(safe_shape("os.fdopen(1)"), False, "os_fdopen_safe")


# ── mmap ──
def test_mmap_leak():
    check(leak_shape("mmap.mmap(-1, 10)"), True, "mmap_leak")


def test_mmap_safe():
    check(safe_shape("mmap.mmap(-1, 10)"), False, "mmap_safe")


# ── ftplib (quit is idiomatic release) ──
def test_ftplib_leak():
    check(leak_shape("ftplib.FTP('host')"), True, "ftplib_leak")


def test_ftplib_safe_quit():
    check(safe_shape("ftplib.FTP('host')", "h.quit()"), False, "ftplib_safe")


# ── smtplib ──
def test_smtp_leak():
    check(leak_shape("smtplib.SMTP('host')"), True, "smtp_leak")


def test_smtp_safe_quit():
    check(safe_shape("smtplib.SMTP('host')", "h.quit()"), False, "smtp_safe")


def test_smtp_ssl_leak():
    check(leak_shape("smtplib.SMTP_SSL('host')"), True, "smtp_ssl_leak")


def test_smtp_ssl_safe_quit():
    check(safe_shape("smtplib.SMTP_SSL('host')", "h.quit()"), False, "smtp_ssl_safe")


# ── telnetlib ──
def test_telnet_leak():
    check(leak_shape("telnetlib.Telnet('host')"), True, "telnet_leak")


def test_telnet_safe():
    check(safe_shape("telnetlib.Telnet('host')"), False, "telnet_safe")


# ── select.poll ──
def test_poll_leak():
    check(leak_shape("select.poll()"), True, "poll_leak")


def test_poll_safe():
    check(safe_shape("select.poll()"), False, "poll_safe")


# ── selectors ──
def test_selector_leak():
    check(leak_shape("selectors.DefaultSelector()"), True, "selector_leak")


def test_selector_safe():
    check(safe_shape("selectors.DefaultSelector()"), False, "selector_safe")


# ── logging handlers ──
def test_file_handler_leak():
    check(leak_shape("logging.FileHandler('x.log')"), True, "file_handler_leak")


def test_file_handler_safe():
    check(safe_shape("logging.FileHandler('x.log')"), False, "file_handler_safe")


def test_rotating_handler_leak():
    check(leak_shape("logging.RotatingFileHandler('x.log')"), True, "rotating_handler_leak")


def test_rotating_handler_safe():
    check(safe_shape("logging.RotatingFileHandler('x.log')"), False, "rotating_handler_safe")


def test_timed_handler_leak():
    check(leak_shape("logging.TimedRotatingFileHandler('x.log')"), True, "timed_handler_leak")


def test_timed_handler_safe():
    check(safe_shape("logging.TimedRotatingFileHandler('x.log')"), False, "timed_handler_safe")


# ── regression: already covered, no new spec needed ──
def test_aiofiles_open_regression():
    check(leak_shape("aiofiles.open('f')"), True, "aiofiles_leak")
    check(safe_shape("aiofiles.open('f')"), False, "aiofiles_safe")
