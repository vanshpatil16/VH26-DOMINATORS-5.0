import textwrap, sys
sys.path.insert(0, '.')
from codegate.ensemble import run_semgrep

src = textwrap.dedent("""
import sqlite3 as db
def leak(p):
    conn = db.connect(p)
    return conn.execute("select 1")
""")
r = run_semgrep(src, 't.py')
print('available:', r['available'])
print('findings:', r['findings'])
print('note:', r.get('note'))
