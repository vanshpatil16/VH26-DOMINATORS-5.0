import socket
import sqlite3


# ============================================================
# 1. SIMPLE LEAK
# Expected: LEAK
# ============================================================

def simple_leak(path):
    f = open(path, "r")
    data = f.read()

    return data


# ============================================================
# 2. EARLY RETURN
# Expected: LEAK
# ============================================================

def early_return(path, error):
    f = open(path, "r")

    if error:
        return "failed"

    data = f.read()
    f.close()

    return data


# ============================================================
# 3. LOOP + EARLY RETURN
# Expected: LEAK
# ============================================================

def loop_leak(files):
    results = []

    for path in files:
        f = open(path, "r")

        results.append(f.read())

        if len(results) > 10:
            return results

        f.close()

    return results


# ============================================================
# 4. EXCEPTION LEAK
# Expected: LEAK
# ============================================================

def exception_leak(path):
    f = open(path, "r")

    try:
        process_file(f)
    except Exception:
        return None

    f.close()


# ============================================================
# 5. EXCEPTION INSIDE EXCEPTION HANDLER
# Expected: LEAK
# ============================================================

def nested_exception_leak(path):
    f = open(path, "r")

    try:
        process_file(f)
    except Exception:
        log_error()       # could itself raise

    f.close()


# ============================================================
# 6. MULTIPLE RESOURCES, ONE FORGOTTEN
# Expected: LEAK
# ============================================================

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


# ============================================================
# 7. RESOURCE OVERWRITTEN
# Expected: LEAK
# ============================================================

def overwritten_resource(path1, path2):
    f = open(path1, "r")

    f = open(path2, "r")

    data = f.read()
    f.close()

    return data


# ============================================================
# 8. RESOURCE PASSED TO ANOTHER FUNCTION
# Expected: POTENTIAL LEAK / OWNERSHIP ANALYSIS
# ============================================================

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


# ============================================================
# 9. SOCKET LEAK
# Expected: LEAK
# ============================================================

def socket_leak():
    s = socket.socket()

    s.connect(("example.com", 80))

    if some_condition():
        return "failed"

    s.close()

    return "done"


# ============================================================
# 10. DATABASE CONNECTION LEAK
# Expected: LEAK
# ============================================================

def database_leak(db_path):
    conn = sqlite3.connect(db_path)

    cursor = conn.cursor()

    if some_condition():
        return None

    cursor.execute("SELECT * FROM users")

    conn.close()

    return "done"


# ============================================================
# 11. SAFE EXPLICIT CLOSE
# Expected: SAFE
# ============================================================

def safe_explicit(path):
    f = open(path, "r")

    try:
        return f.read()
    finally:
        f.close()


# ============================================================
# 12. SAFE CONTEXT MANAGER
# Expected: SAFE
# ============================================================

def safe_with(path):
    with open(path, "r") as f:
        return f.read()


# ============================================================
# 13. SAFE MULTIPLE RESOURCES
# Expected: SAFE
# ============================================================

def safe_multiple(path1, path2):
    with open(path1, "r") as f1:
        with open(path2, "r") as f2:
            return f1.read() + f2.read()


# ============================================================
# 14. LOOP WITH SAFE CLEANUP
# Expected: SAFE
# ============================================================

def safe_loop(files):
    results = []

    for path in files:
        with open(path, "r") as f:
            results.append(f.read())

    return results


# ============================================================
# 15. COMPLEX NESTED CASE
# Expected: LEAK
# ============================================================

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


# ============================================================
# MOCK FUNCTIONS
# ============================================================

def process_file(f):
    data = f.read()

    if "CRASH" in data:
        raise RuntimeError("processing failed")

    return data


def process_and_maybe_close(f):
    data = f.read()

    if "SECRET" in data:
        return data

    f.close()

    return data


def log_error():
    print("error")


def handle_error():
    print("handled")


def some_condition():
    return False


def should_stop(data):
    return "STOP" in data


def should_close(data):
    return True
