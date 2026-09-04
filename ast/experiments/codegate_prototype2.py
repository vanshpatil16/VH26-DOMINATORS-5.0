import sys
sys.path.insert(0, 'Scalpel/src')
from scalpel.cfg import CFGBuilder
import ast, textwrap

def is_acquire(stmt):
    if isinstance(stmt, ast.Assign) and len(stmt.targets)==1 and isinstance(stmt.targets[0], ast.Name):
        var = stmt.targets[0].id
        if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id=="open":
            return var, "open"
    return None

def is_release(stmt, aliases):
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute) and call.func.attr=="close" and isinstance(call.func.value, ast.Name) and call.func.value.id in aliases:
            return True
    return False

# Test reassign case more carefully
code = textwrap.dedent('''
def reassign_leak(path):
    f = open(path)
    f = open(path)
    f.close()
    return 1
''')
b = CFGBuilder()
cfg = b.build_from_src('t', code)
fcfg = list(cfg.functioncfgs.values())[0]
blocks = fcfg.get_all_blocks()
print("Blocks:")
for blk in blocks:
    for s in blk.statements:
        print(f"  L{s.lineno} {ast.dump(s)[:120]}")

# Need to handle sequential acquires in same block: second acquire kills first without closing?
# Our current DFS starts at each acquire and looks forward for close, but for f=open at line 3, the path includes f=open at line 4 (second acquire) then f.close -> our logic sees close as covering first acquire, but actually first acquire is leaked because reassigned before close

# We need ownership tracking: resource lifetime ends at reassignment or at close or at return
# Simple rule: after f = open(path) at line 3, if next statement is f = open(path) (reassign), then first resource is lost -> leak even if later close exists (close closes second resource)

# How to detect? For each acquire, find next assignment to same var before close -> leak

# More generally: track live resources
print("\n=== Need dataflow ===")
# Approach: simulate execution along each path, tracking live resource handles
# When we encounter f = open(), push resource onto live set with id (var, lineno)
# When we encounter f.close() where f in aliases of live resources, pop
# When we encounter g = f where f is live, add alias mapping but not new resource
# When we encounter f = <something not open>, kill f's resource if live -> leak if killed without close
# When we encounter reassignment f = open() again, first check if f already live -> leak for previous

# Also need ownership transfer: return f, or helper(f) where helper closes? For hackathon, we can flag return f as "transferred" not leak (or warn with ownership)

# Let's prototype live tracking

def analyze_live(func_code, func_name):
    b = CFGBuilder()
    cfg = b.build_from_src('t', func_code)
    fcfg = list(cfg.functioncfgs.values())[0] if list(cfg.functioncfgs.values()) else cfg
    blocks = fcfg.get_all_blocks()
    id2block = {blk.id: blk for blk in blocks}

    # Build successors map
    succ = {blk.id: [e.target for e in blk.exits] for blk in blocks}
    preds = {blk.id: [p.source for p in blk.predecessors] for blk in blocks}

    # Find entry
    entry = fcfg.entryblock

    # We'll enumerate paths but with stateful live set
    # Use DFS with state copying
    leaks = []

    def process_block(block, live, aliases, path):
        new_live = set(live)
        new_aliases = dict(aliases)  # var -> resource id it points to
        # Actually aliases: resource_id -> set(vars) or var -> resource_id?
        # Simplify: live is set of (var, resource_id) where resource_id is lineno of acquire
        # aliases tracks var -> resource_id
        # For g = f where f maps to resource_id, then g also maps to same resource_id, and live gets (g, resource_id)

        # Need resource tracking: each acquire creates new resource id
        leaks_here = []

        # Iterate statements in order
        for stmt in block.statements:
            # Check assign
            if isinstance(stmt, ast.Assign) and len(stmt.targets)==1 and isinstance(stmt.targets[0], ast.Name):
                lhs = stmt.targets[0].id
                rhs = stmt.value
                if isinstance(rhs, ast.Call) and isinstance(rhs.func, ast.Name) and rhs.func.id=="open":
                    # acquire
                    # if lhs already maps to a live resource, that previous resource is leaked (overwritten before close)
                    if lhs in new_aliases:
                        prev_res = new_aliases[lhs]
                        if prev_res in [r for (v,r) in new_live]:
                            # leaked previous
                            leaks_here.append((prev_res, stmt.lineno, f"reassign {lhs} leaks previous acquire at {prev_res}"))
                            # remove previous from live
                            new_live = {(v,r) for (v,r) in new_live if r != prev_res or v != lhs}  # but aliases sharing resource? Remove lhs mapping only
                            # Actually if g also points to prev_res, it still lives via g? But lhs reassigned, g still holds? Need more precise
                            # For simplicity, if any var still aliases prev_res, keep live
                            # Check if any other var in aliases still points to prev_res
                            other_holds = any(v2 != lhs and res == prev_res for v2, res in new_aliases.items())
                            if not other_holds:
                                new_live = {(v,r) for (v,r) in new_live if r != prev_res}
                    # Create new resource
                    new_res_id = stmt.lineno
                    new_live.add((lhs, new_res_id))
                    new_aliases[lhs] = new_res_id
                    # print(f"  Acquire {lhs} -> res {new_res_id} at line {stmt.lineno}")
                elif isinstance(rhs, ast.Name):
                    # alias: g = f
                    rhs_var = rhs.id
                    if rhs_var in new_aliases:
                        res = new_aliases[rhs_var]
                        # if lhs already held another resource, leak that previous?
                        if lhs in new_aliases and new_aliases[lhs] != res:
                            prev_res = new_aliases[lhs]
                            # leak previous if no other holder and not closed?
                            # For now leak if overwritten
                            leaks_here.append((prev_res, stmt.lineno, f"alias reassign {lhs} leaks prev {prev_res}"))
                            # remove old if no other holder
                            other_holds = any(v2 != lhs and r == prev_res for v2, r in new_aliases.items())
                            if not other_holds:
                                new_live = {(v,r) for (v,r) in new_live if r != prev_res}
                        new_aliases[lhs] = res
                        new_live.add((lhs, res))
                    else:
                        # rhs not resource, so lhs no longer resource handle? Kill
                        if lhs in new_aliases:
                            prev_res = new_aliases[lhs]
                            other_holds = any(v2 != lhs and r == prev_res for v2, r in new_aliases.items())
                            if not other_holds:
                                # leaked? If we overwrite resource holder with non-resource, it's like losing handle -> leak unless already closed
                                leaks_here.append((prev_res, stmt.lineno, f"kill {lhs} by non-resource assign leaks {prev_res}"))
                                new_live = {(v,r) for (v,r) in new_live if r != prev_res}
                            del new_aliases[lhs]
                else:
                    # lhs = something else (e.g., 1, data = f.read()) - if lhs was resource handle, it's killed -> leak
                    if lhs in new_aliases:
                        prev_res = new_aliases[lhs]
                        other_holds = any(v2 != lhs and r == prev_res for v2, r in new_aliases.items())
                        if not other_holds:
                            leaks_here.append((prev_res, stmt.lineno, f"kill {lhs} leaks {prev_res}"))
                            new_live = {(v,r) for (v,r) in new_live if r != prev_res}
                        del new_aliases[lhs]
                        # also remove from live set specific var, but keep resource if other alias holds?
                        new_live = {(v,r) for (v,r) in new_live if not (v==lhs and r==prev_res)}
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Attribute) and call.func.attr=="close" and isinstance(call.func.value, ast.Name):
                    clos_var = call.func.value.id
                    if clos_var in new_aliases:
                        res = new_aliases[clos_var]
                        # closing resource res via any alias should close for all aliases
                        # Remove all vars mapping to res from live?
                        vars_to_close = [v for v,r in new_aliases.items() if r == res]
                        for v in vars_to_close:
                            del new_aliases[v]
                        new_live = {(v,r) for (v,r) in new_live if r != res}
                        # print(f"  Close via {clos_var} closes res {res} vars {vars_to_close}")
            elif isinstance(stmt, ast.Return):
                # For now, if return value is a resource var, consider ownership transferred -> not leak
                # If return is reachable with live resources not returned, those are leaks
                pass

        return new_live, new_aliases, leaks_here

    # DFS enumeration with state
    visited_leaks = set()
    def dfs(block, live, aliases, path, visited):
        if block.id in visited:
            return # loop - avoid infinite
        visited = visited | {block.id}
        path = path + [block.id]
        new_live, new_aliases, leaks_here = process_block(block, live, aliases, path)
        for lk in leaks_here:
            print(f"  Leak inside Block {block.id} path {path}: {lk}")
            visited_leaks.add(lk[0])

        # If at final block, any remaining live is leak (reaching exit without close)
        if block in fcfg.finalblocks or not block.exits:
            if new_live:
                for (var,res) in new_live:
                    print(f"  Leak at exit Block {block.id} path {path}: resource {res} via {var} not closed")
                    visited_leaks.add(res)
            return

        for edge in block.exits:
            dfs(edge.target, set(new_live), dict(new_aliases), path, visited)

    dfs(entry, set(), {}, [], set())
    print(f"Final leaks: {visited_leaks}")
    return visited_leaks

test_cases = [
    ("reassign_leak", textwrap.dedent('''
def reassign_leak(path):
    f = open(path)
    f = open(path)
    f.close()
    return 1
''')),
    ("alias_safe", textwrap.dedent('''
def alias_safe(path):
    f = open(path)
    g = f
    g.close()
    return 1
''')),
    ("leak_simple", textwrap.dedent('''
def leak_simple(path):
    f = open(path)
    data = f.read()
    if not data:
        return None
    f.close()
    return data
''')),
    ("transfer", textwrap.dedent('''
def transfer(path):
    f = open(path)
    return f
''')),
]

for name, code in test_cases:
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    analyze_live(code, name)

