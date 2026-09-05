"""
Prototype CodeGate leak detector on top of Scalpel CFG + simple alias tracking.
This is the core logic we will productize.

Strategy:
- Use Scalpel CFG for control flow
- Do path-sensitive analysis: for each acquire (e.g., f = open()), check if EVERY path to every exit contains a release (f.close() or alias close)
- Handle alias: track assignments g = f, h = g, etc.
"""
import sys
sys.path.insert(0, 'Scalpel/src')
from scalpel.cfg import CFGBuilder
import ast, textwrap

# configurable resources
RESOURCE_CONFIG = {
    "open": {"release": "close"},
    "socket.socket": {"release": "close"},
    "open": {"release": "close"},
}

def is_acquire(stmt):
    """Check if stmt is f = open(...) (or similar acquire)"""
    if isinstance(stmt, ast.Assign):
        if len(stmt.targets)==1 and isinstance(stmt.targets[0], ast.Name):
            var = stmt.targets[0].id
            if isinstance(stmt.value, ast.Call):
                # check func name
                func = stmt.value.func
                if isinstance(func, ast.Name) and func.id in ("open",):
                    return var, func.id
                # for now only open
                # TODO: configurable via qualified names
        # also handle with? No, with is safe by construction, so we skip
    return None

def is_release(stmt, aliases):
    """Check if stmt is x.close() where x is in aliases set"""
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute) and call.func.attr == "close":
            if isinstance(call.func.value, ast.Name):
                name = call.func.value.id
                if name in aliases:
                    return True
    return False

def find_aliases(blocks, resource_var):
    """Naive alias tracking: find all vars that are assigned from resource_var (direct or transitive)"""
    aliases = {resource_var}
    changed = True
    # Collect all assignments
    assignments = []
    for blk in blocks:
        for stmt in blk.statements:
            if isinstance(stmt, ast.Assign) and len(stmt.targets)==1 and isinstance(stmt.targets[0], ast.Name):
                lhs = stmt.targets[0].id
                if isinstance(stmt.value, ast.Name):
                    rhs = stmt.value.id
                    assignments.append((lhs, rhs, stmt.lineno))
    # transitive closure
    while changed:
        changed = False
        for lhs, rhs, _ in assignments:
            if rhs in aliases and lhs not in aliases:
                aliases.add(lhs)
                changed = True
    return aliases

def has_release_in_block(block, aliases):
    for stmt in block.statements:
        if is_release(stmt, aliases):
            return True
    return False

def detect_leaks_for_func(func_code, func_name="test"):
    b = CFGBuilder()
    cfg = b.build_from_src('t', func_code)
    # Find func cfg
    fcfg = None
    for (_, n), c in cfg.functioncfgs.items():
        if n == func_name:
            fcfg = c
            break
    if not fcfg:
        # Use first
        fcfg = list(cfg.functioncfgs.values())[0]
        func_name = fcfg.name
    print(f"\n=== Analyzing {func_name} ===")
    blocks = fcfg.get_all_blocks()
    print(f"Blocks: {len(blocks)} finals {[b.id for b in fcfg.finalblocks]}")
    for blk in blocks:
        print(f"  Block {blk.id} at {blk.at()} { [type(s).__name__ + ':' + str(getattr(s,'lineno','?')) for s in blk.statements]} -> {[e.target.id for e in blk.exits]} final={blk in fcfg.finalblocks}")

    # Find acquires
    acquires = []
    for blk in blocks:
        for stmt in blk.statements:
            acq = is_acquire(stmt)
            if acq:
                var, api = acq
                acquires.append((blk, stmt, var, api))
                print(f"  Found acquire {var} = {api} at line {stmt.lineno} in Block {blk.id}")

    leaks = []
    for acq_blk, acq_stmt, var, api in acquires:
        aliases = find_aliases(blocks, var)
        print(f"\n  Checking acquire {var}={api} at line {acq_stmt.lineno}, aliases={aliases}")
        # Need to check all paths from acq_blk to each final block
        # If acquire is inside block with other stmts, the close after it in same block may still be on path?
        # Simplistic: enumerate paths via DFS, check if each path contains a release after the acquire

        # Build graph
        id2block = {b.id: b for b in blocks}
        # DFS enumerate paths (watch for loops -> need visited set)
        # For resource leak, we need to prove that EVERY path from acquire point to exit has a release
        # If there exists a path without release, it's a leak.
        # Handle loops conservatively: if loop without release, it's leak due to at least one iteration without?

        # For now, enumerate acyclic paths with loop detection

        def dfs(current, visited, has_release_so_far, path):
            # Avoid infinite loops, but track that loop may be traversed 0 or 1 times? For leak we consider existence of path, so we can visit loop once
            if current.id in visited:
                return []  # prevent infinite recursion, but this may miss leaks in loops? For hackathon, OK
            visited = visited | {current.id}
            path = path + [current.id]

            # Check if this block contains release after acquire point
            # If we are at acq_blk, we need to check statements after acq_stmt
            contains_release = False
            if current == acq_blk:
                # find index of acq_stmt
                idx = current.statements.index(acq_stmt)
                for stmt in current.statements[idx+1:]:
                    if is_release(stmt, aliases):
                        contains_release = True
                        break
            else:
                contains_release = has_release_in_block(current, aliases)

            has_release = has_release_so_far or contains_release

            # If this is final block, record if leaked
            if current in fcfg.finalblocks:
                # Also handle phantom predecessor trick: if block final and no exits, it's exit
                return [(path, has_release)]

            # Also need to handle case where block has no exits but not in finalblocks? (should be final)
            if not current.exits:
                return [(path, has_release)]

            paths = []
            for edge in current.exits:
                paths.extend(dfs(edge.target, visited, has_release, path))
            return paths

        # Start DFS from acq block's successors? Or include acq block itself
        # Actually path starts at acq_blk, with has_release considering statements after acquire in same block
        all_paths = dfs(acq_blk, set(), False, [])
        # However this misses paths that go through predecessors? No, we start at acquire block forward only, which is correct
        # Because any path from entry to exit that includes acquire must go through acq_blk forward to exit

        # But need to ensure we capture all downstream paths irrespective of how we entered acq_blk (there is single entry to acq_blk in linear case)
        # For more complex, ok.

        print(f"    Enumerated {len(all_paths)} paths from Block {acq_blk.id}:")
        leaked = False
        for p, has_rel in all_paths:
            status = "SAFE" if has_rel else "LEAK"
            print(f"      Path {p} -> {status}")
            if not has_rel:
                leaked = True

        if leaked:
            print(f"    ==> LEAK DETECTED for {var} at line {acq_stmt.lineno}")
            leaks.append((var, acq_stmt.lineno, acquires))
        else:
            print(f"    ==> SAFE for {var} at line {acq_stmt.lineno}")

        # Also handle case: if acquire is not in entry block, but there are multiple ways to reach acquire? We already handle
        # Known limitation: if acquire inside branch, our DFS still works

    return leaks

# Test cases

test_cases = [
    ("leak_simple", textwrap.dedent('''
def leak_simple(path):
    f = open(path)
    data = f.read()
    if not data:
        return None
    f.close()
    return data
'''), True),
    ("safe_close_both", textwrap.dedent('''
def safe_close_both(path):
    f = open(path)
    data = f.read()
    if not data:
        f.close()
        return None
    f.close()
    return data
'''), False),
    ("safe_with", textwrap.dedent('''
def safe_with(path):
    with open(path) as f:
        data = f.read()
    return data
'''), False), # with not detected as acquire, so no leak reported -> correct by definition (with is safe)
    ("alias_safe", textwrap.dedent('''
def alias_safe(path):
    f = open(path)
    g = f
    g.close()
    return 1
'''), False),
    ("alias_leak_branch", textwrap.dedent('''
def alias_leak_branch(path):
    f = open(path)
    g = f
    if True:
        g.close()
    return 1
'''), True), # Wait if True always, but CFG has both branches? if True: branch still has both? Actually if True: has one path via if and one not? Let's see
    ("return_resource", textwrap.dedent('''
def return_resource(path):
    f = open(path)
    return f
'''), True), # Ownership transferred, but our simple checker will flag as leak. Need ownership rule: return f => not leak?
    ("reassign_leak", textwrap.dedent('''
def reassign_leak(path):
    f = open(path)
    f = open(path)
    f.close()
    return 1
'''), True), # First open leaked
    ("loop_close", textwrap.dedent('''
def loop_close(path):
    f = open(path)
    for i in range(3):
        print(i)
    f.close()
    return 1
'''), False),
]

for name, code, expect_leak in test_cases:
    leaks = detect_leaks_for_func(code, name)
    has_leak = len(leaks) > 0
    status = "PASS" if has_leak == expect_leak else "FAIL"
    print(f"\n>>> Test {name}: expect_leak={expect_leak} got_leak={has_leak} => {status}")

