"""Synthesize `dataset/real_code/escapes/` — the population the model serves.

Every other corpus generator produces sites the *rules* decide. `synthesize.py`
emits provable SAFE, `mutate.py` emits provable DEFINITE_LEAK. Neither is what
the confidence model is asked at scan time: `leakguard/scoring.py` consults it
for exactly one verdict, `UNKNOWN` — ownership left the function and no sound
intraprocedural analysis can follow it.

Before this generator the corpus held **three** UNKNOWN rows out of 946, so the
model was fitted on a distribution it never sees in production and learned to be
a worse copy of the rules. These templates fix that: each renders one whole
module where the handle escapes (returned, yielded, put in a container, stored in
a module global, handed to a callee that only sometimes releases it) *and* the
recipient is visible in the same module, so a human can state the ground truth
the analyser cannot prove.

Two invariants keep the labels honest:

* **The verdict is asserted, not assumed.** A rendered combination is written
  only if the analyser really returns UNKNOWN on it. Anything the rules can
  actually decide is dropped rather than labelled by hand.
* **Truth comes from the recipient.** label 1 means the module genuinely leaks
  (the caller drops the handle, the registry is never drained); label 0 means it
  genuinely releases. The escape shape alone never decides the label — both
  labels are rendered over the same escape kinds, so the model cannot key on
  "returns a handle" and score well.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leakguard.detector import VERDICT_UNKNOWN, analyse_module  # noqa: E402
from tools.corpus_lib import (  # noqa: E402
    REAL_DIR,
    ROOT,
    Sample,
    build_sample,
    write_manifest,
)
from tools.synthesize import RESOURCES, Res  # noqa: E402

ESCAPE_DIR = os.path.join(REAL_DIR, "escapes")

#: Resources to cross the templates with. A subset of the full registry on
#: purpose: the point of this corpus is escape *shape* coverage, and rendering
#: all 40 resources against 11 templates would swamp the rest of the dataset.
RESOURCE_KEYS = (
    "file_text", "file_gzip", "file_temp", "socket_raw", "socket_connect",
    "http_conn", "session", "sqlite", "postgres", "redis_client", "mongo",
    "file_zip",
)

CONTEXTS: Tuple[Tuple[str, str], ...] = (("ingest", "payload"), ("billing", "payload"))

PARAMS = (
    "path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, "
    "items=(), flag=False"
)


@dataclass(frozen=True)
class Template:
    """One escape shape plus the ground truth about what the recipient does."""

    key: str
    label: int                  # 1 = the module really leaks, 0 = really releases
    edge_cases: Tuple[str, ...]
    note: str
    render: Callable[[Res, str, str], str]


def _imports(res: Res, extra: Tuple[str, ...] = ()) -> str:
    lines = sorted(set(res.imports) | set(extra))
    return ("\n".join(lines) + "\n\n\n") if lines else "\n"


def _use(res: Res, var: str) -> str:
    return res.use.replace(res.var + ".", var + ".")


# --------------------------------------------------------------------------- #
# return / yield escapes
# --------------------------------------------------------------------------- #


def t_return_caller_closes(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Factory hands ownership to a caller that closes it."""\n\n'
        + _imports(res, ("import contextlib",))
        + "def _acquire_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    return %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    with contextlib.closing(_acquire_%s(path, host, port)) as %s:\n"
        % (res.key, res.var)
        + "        %s\n" % res.use
        + "    return %s\n" % noun
    )


def t_return_caller_drops(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Factory hands ownership to a caller that never releases it."""\n\n'
        + _imports(res)
        + "def _acquire_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    return %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = _acquire_%s(path, host, port)\n" % (res.var, res.key)
        + "    %s\n" % res.use
        + "    return %s\n" % noun
    )


def t_return_owned_by_class(res: Res, fn: str, noun: str) -> str:
    cls = "".join(part.capitalize() for part in fn.split("_")) + "Owner"
    return (
        '"""Factory output adopted by a class that closes it."""\n\n'
        + _imports(res)
        + "def _acquire_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    return %s\n\n\n" % res.var
        + "class %s:\n" % cls
        + "    def __init__(self, %s):\n" % PARAMS
        + "        self.%s = _acquire_%s(path, host, port)\n\n" % (res.var, res.key)
        + "    def %s(self):\n" % fn
        + "        %s\n" % _use(res, "self." + res.var)
        + "        return %s\n\n" % noun
        + "    def close(self):\n"
        + "        self.%s.%s()\n" % (res.var, res.closer)
    )


def t_yield_consumer_closes(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Generator yields the handle; the consumer releases it."""\n\n'
        + _imports(res)
        + "def _stream_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    yield %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    for %s in _stream_%s(path, host, port):\n" % (res.var, res.key)
        + "        try:\n"
        + "            %s\n" % res.use
        + "        finally:\n"
        + "            %s.%s()\n" % (res.var, res.closer)
        + "    return %s\n" % noun
    )


def t_yield_consumer_drops(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Generator yields the handle; the consumer walks away from it."""\n\n'
        + _imports(res)
        + "def _stream_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    yield %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    for %s in _stream_%s(path, host, port):\n" % (res.var, res.key)
        + "        %s\n" % res.use
        + "        break\n"
        + "    return %s\n" % noun
    )


# --------------------------------------------------------------------------- #
# container / global escapes
# --------------------------------------------------------------------------- #


def t_container_drained(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Handles collected into a list the caller drains in a finally."""\n\n'
        + _imports(res)
        + "def _collect_%s(%s):\n" % (res.key, PARAMS)
        + "    opened = []\n"
        + "    for item in items:\n"
        + "        %s = %s\n" % (res.var, res.ctor)
        + "        opened.append(%s)\n" % res.var
        + "    return opened\n\n\n"
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    opened = _collect_%s(path, host, port, items=items)\n" % res.key
        + "    try:\n"
        + "        for %s in opened:\n" % res.var
        + "            %s\n" % res.use
        + "    finally:\n"
        + "        for %s in opened:\n" % res.var
        + "            %s.%s()\n" % (res.var, res.closer)
        + "    return %s\n" % noun
    )


def t_container_never_drained(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Handles collected into a list nothing ever drains."""\n\n'
        + _imports(res)
        + "def _collect_%s(%s):\n" % (res.key, PARAMS)
        + "    opened = []\n"
        + "    for item in items:\n"
        + "        %s = %s\n" % (res.var, res.ctor)
        + "        opened.append(%s)\n" % res.var
        + "    return opened\n\n\n"
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    opened = _collect_%s(path, host, port, items=items)\n" % res.key
        + "    for %s in opened:\n" % res.var
        + "        %s\n" % res.use
        + "    return %s\n" % noun
    )


def t_global_registry_shutdown(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Module-level registry with a shutdown that releases every entry."""\n\n'
        + _imports(res)
        + "_REGISTRY = {}\n\n\n"
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    _REGISTRY[key] = %s\n" % res.var
        + "    %s\n" % res.use
        + "    return %s\n\n\n" % noun
        + "def shutdown():\n"
        + "    for %s in _REGISTRY.values():\n" % res.var
        + "        %s.%s()\n" % (res.var, res.closer)
        + "    _REGISTRY.clear()\n"
    )


def t_global_registry_orphan(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Module-level registry nothing ever shuts down."""\n\n'
        + _imports(res)
        + "_REGISTRY = {}\n\n\n"
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    _REGISTRY[key] = %s\n" % res.var
        + "    %s\n" % res.use
        + "    return %s\n\n\n" % noun
        + "def lookup(key=None):\n"
        + "    return _REGISTRY.get(key)\n"
    )


# --------------------------------------------------------------------------- #
# partially-releasing callee
# --------------------------------------------------------------------------- #


def t_callee_partial_release(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Callee releases the handle on one branch only."""\n\n'
        + _imports(res)
        + "def _maybe_release(%s, flag=False):\n" % res.var
        + "    if flag:\n"
        + "        %s.%s()\n\n\n" % (res.var, res.closer)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    %s\n" % res.use
        + "    _maybe_release(%s, flag)\n" % res.var
        + "    return %s\n" % noun
    )


def t_callee_partial_then_guarded(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Callee may release; the caller also releases under a guard."""\n\n'
        + _imports(res)
        + "def _maybe_release(%s, flag=False):\n" % res.var
        + "    if flag:\n"
        + "        %s.%s()\n\n\n" % (res.var, res.closer)
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    try:\n"
        + "        %s\n" % res.use
        + "        _maybe_release(%s, flag)\n" % res.var
        + "        return %s\n" % noun
        + "    finally:\n"
        + "        %s.%s()\n" % (res.var, res.closer)
    )


def t_return_caller_closes_in_finally(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Factory return released by the caller in a finally."""\n\n'
        + _imports(res)
        + "def _acquire_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    return %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = _acquire_%s(path, host, port)\n" % (res.var, res.key)
        + "    try:\n"
        + "        %s\n" % res.use
        + "        return %s\n" % noun
        + "    finally:\n"
        + "        %s.%s()\n" % (res.var, res.closer)
    )


def t_return_caller_uses_exit_stack(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Factory return registered on an ExitStack by the caller."""\n\n'
        + _imports(res, ("import contextlib",))
        + "def _acquire_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    return %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    with contextlib.ExitStack() as stack:\n"
        + "        %s = stack.enter_context(\n" % res.var
        + "            contextlib.closing(_acquire_%s(path, host, port)))\n" % res.key
        + "        %s\n" % res.use
        + "        return %s\n" % noun
    )


def t_return_stored_unowned(res: Res, fn: str, noun: str) -> str:
    cls = "".join(part.capitalize() for part in fn.split("_")) + "Holder"
    return (
        '"""Factory return stored on a class that never releases it."""\n\n'
        + _imports(res)
        + "def _acquire_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    return %s\n\n\n" % res.var
        + "class %s:\n" % cls
        + "    def __init__(self, %s):\n" % PARAMS
        + "        self.%s = _acquire_%s(path, host, port)\n\n" % (res.var, res.key)
        + "    def %s(self):\n" % fn
        + "        %s\n" % _use(res, "self." + res.var)
        + "        return %s\n" % noun
    )


def t_return_reexported(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Factory return passed straight back out, still unreleased."""\n\n'
        + _imports(res)
        + "def _acquire_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    return %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    %s = _acquire_%s(path, host, port)\n" % (res.var, res.key)
        + "    %s\n" % res.use
        + "    return %s\n" % res.var
    )


def t_yield_consumer_closes_after_loop(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Generator yields the handle; consumer keeps then closes it."""\n\n'
        + _imports(res)
        + "def _stream_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    yield %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    kept = None\n"
        + "    for %s in _stream_%s(path, host, port):\n" % (res.var, res.key)
        + "        kept = %s\n" % res.var
        + "        %s\n" % res.use
        + "    kept.%s()\n" % res.closer
        + "    return %s\n" % noun
    )


def t_yield_consumer_collects(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Generator yields the handle; consumer only stockpiles it."""\n\n'
        + _imports(res)
        + "def _stream_%s(%s):\n" % (res.key, PARAMS)
        + "    %s = %s\n" % (res.var, res.ctor)
        + "    yield %s\n\n\n" % res.var
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    kept = []\n"
        + "    for %s in _stream_%s(path, host, port):\n" % (res.var, res.key)
        + "        %s\n" % res.use
        + "        kept.append(%s)\n" % res.var
        + "    return kept\n"
    )


def t_container_drained_by_helper(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Collected handles released by a named cleanup helper."""\n\n'
        + _imports(res)
        + "def close_all(handles=()):\n"
        + "    for entry in handles:\n"
        + "        entry.%s()\n\n\n" % res.closer
        + "def _collect_%s(%s):\n" % (res.key, PARAMS)
        + "    opened = []\n"
        + "    for item in items:\n"
        + "        %s = %s\n" % (res.var, res.ctor)
        + "        opened.append(%s)\n" % res.var
        + "    return opened\n\n\n"
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    opened = _collect_%s(path, host, port, items=items)\n" % res.key
        + "    try:\n"
        + "        for %s in opened:\n" % res.var
        + "            %s\n" % res.use
        + "    finally:\n"
        + "        close_all(opened)\n"
        + "    return %s\n" % noun
    )


def t_container_returned_unused(res: Res, fn: str, noun: str) -> str:
    return (
        '"""Collected handles handed back and then ignored."""\n\n'
        + _imports(res)
        + "def _collect_%s(%s):\n" % (res.key, PARAMS)
        + "    opened = []\n"
        + "    for item in items:\n"
        + "        %s = %s\n" % (res.var, res.ctor)
        + "        opened.append(%s)\n" % res.var
        + "    return opened\n\n\n"
        + "def %s(%s):\n" % (fn, PARAMS)
        + "    opened = _collect_%s(path, host, port, items=items)\n" % res.key
        + "    return len(opened)\n"
    )


TEMPLATES: Tuple[Template, ...] = (
    Template("return_caller_closes", 0, ("EC-OWN-03", "EC-INTER-02"),
             "factory return adopted by contextlib.closing in the caller",
             t_return_caller_closes),
    Template("return_caller_drops", 1, ("EC-OWN-03", "EC-INTER-03"),
             "factory return dropped by the caller without any release",
             t_return_caller_drops),
    Template("return_owned_by_class", 0, ("EC-OWN-01", "EC-OWN-03"),
             "factory return adopted as an attribute the class closes",
             t_return_owned_by_class),
    Template("yield_consumer_closes", 0, ("EC-GEN-03",),
             "generator yields the handle, consumer closes it in a finally",
             t_yield_consumer_closes),
    Template("yield_consumer_drops", 1, ("EC-GEN-04",),
             "generator yields the handle, consumer abandons it after one item",
             t_yield_consumer_drops),
    Template("container_drained", 0, ("EC-CONT-01",),
             "handles collected into a list the caller drains in a finally",
             t_container_drained),
    Template("container_never_drained", 1, ("EC-CONT-02",),
             "handles collected into a list nothing releases",
             t_container_never_drained),
    Template("global_registry_shutdown", 0, ("EC-GLOB-01",),
             "module registry with a shutdown that closes every entry",
             t_global_registry_shutdown),
    Template("global_registry_orphan", 1, ("EC-GLOB-02",),
             "module registry with no shutdown path at all",
             t_global_registry_orphan),
    Template("callee_partial_release", 1, ("EC-INTER-04",),
             "callee closes on one branch only, so the other branch leaks",
             t_callee_partial_release),
    Template("callee_partial_then_guarded", 0, ("EC-INTER-05",),
             "callee may close, but the caller's finally closes unconditionally",
             t_callee_partial_then_guarded),
    Template("return_caller_closes_in_finally", 0, ("EC-OWN-03", "EC-CF-05"),
             "factory return released by the caller in a finally",
             t_return_caller_closes_in_finally),
    Template("return_caller_uses_exit_stack", 0, ("EC-OWN-03", "EC-CTX-05"),
             "factory return registered on the caller's ExitStack",
             t_return_caller_uses_exit_stack),
    Template("return_stored_unowned", 1, ("EC-OWN-05",),
             "factory return stored on a class with no closer at all",
             t_return_stored_unowned),
    Template("return_reexported", 1, ("EC-OWN-04",),
             "factory return handed straight back out, still unreleased",
             t_return_reexported),
    Template("yield_consumer_closes_after_loop", 0, ("EC-GEN-05",),
             "consumer keeps the yielded handle and closes it after the loop",
             t_yield_consumer_closes_after_loop),
    Template("yield_consumer_collects", 1, ("EC-GEN-06",),
             "consumer stockpiles yielded handles and releases none",
             t_yield_consumer_collects),
    Template("container_drained_by_helper", 0, ("EC-CONT-03", "EC-INTER-06"),
             "collected handles released by a named cleanup helper",
             t_container_drained_by_helper),
    Template("container_returned_unused", 1, ("EC-CONT-04",),
             "collected handles handed back to a caller that ignores them",
             t_container_returned_unused),
)


def _resources() -> List[Res]:
    by_key = {res.key: res for res in RESOURCES}
    return [by_key[key] for key in RESOURCE_KEYS if key in by_key]


def _prune_unclaimed(samples: List[Sample]) -> None:
    """Drop files a previous run wrote that this run no longer claims."""
    claimed = {os.path.normcase(os.path.join(ROOT, s.path.replace("/", os.sep)))
               for s in samples}
    if not os.path.isdir(ESCAPE_DIR):
        return
    for dirpath, _dirnames, filenames in os.walk(ESCAPE_DIR):
        for name in filenames:
            if name.endswith(".py"):
                abs_path = os.path.join(dirpath, name)
                if os.path.normcase(abs_path) not in claimed:
                    os.remove(abs_path)
    for dirpath, dirnames, filenames in os.walk(ESCAPE_DIR, topdown=False):
        if dirpath != ESCAPE_DIR and not dirnames and not filenames:
            os.rmdir(dirpath)


def main() -> int:
    samples: List[Sample] = []
    skipped: List[str] = []
    index = 0
    for template in TEMPLATES:
        for res in _resources():
            for context, noun in CONTEXTS:
                fn = "%s_%s" % (context, res.key)
                source = template.render(res, fn, noun)
                analysis = analyse_module(source, "<escape>")
                if analysis.parse_error:
                    skipped.append("%s/%s: %s"
                                   % (template.key, res.key, analysis.parse_error))
                    continue
                unknown = sorted(site.line for site in analysis.sites
                                 if site.verdict == VERDICT_UNKNOWN)
                decided = [site.verdict for site in analysis.sites
                           if site.verdict != VERDICT_UNKNOWN]
                # The whole point of this corpus is the rules abstaining. If they
                # did not, the sample belongs in one of the other generators and
                # hand-labelling it here would be a fabricated label.
                if not unknown or decided:
                    skipped.append("%s/%s: verdicts=%s"
                                   % (template.key, res.key,
                                      sorted({s.verdict for s in analysis.sites})))
                    continue
                index += 1
                name = "%s__%s__%s.py" % (template.key, res.key, context)
                abs_path = os.path.join(ESCAPE_DIR, template.key, name)
                samples.append(
                    build_sample(
                        sample_id="E-%04d" % index,
                        abs_path=abs_path,
                        folder="real_code",
                        origin="escapes",
                        family="escape:%s" % template.key,
                        label=template.label,
                        source=source,
                        edge_cases=list(template.edge_cases),
                        note=template.note,
                        explicit_leak_lines=unknown if template.label else [],
                        explicit_unknown_lines=unknown,
                    )
                )
    _prune_unclaimed(samples)
    written = write_manifest(os.path.join(ESCAPE_DIR, "manifest.jsonl"), samples)
    positives = sum(s.label for s in samples)
    print("real_code/escapes: %d samples (%d leak / %d released) across %d shapes"
          % (written, positives, written - positives, len(TEMPLATES)))
    if skipped:
        print("skipped %d combinations the rules could decide:" % len(skipped))
        for line in skipped[:12]:
            print("  %s" % line)
        if len(skipped) > 12:
            print("  ... %d more" % (len(skipped) - 12))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
