"""Scalpel CFG wrapper -- now backed by the stdlib builder in codegate.cfg.

History: this module used to monkey-patch two Scalpel bugs (visit_Try crashing
on an empty finalbody, visit_Return leaving a phantom empty block).  Scalpel
cannot be installed on Python >= 3.9 at all: python-scalpel pins typed-ast,
which publishes no wheels and needs a C toolchain to build.  The CFG is now
built by codegate.cfg, which reproduces the same public surface and avoids both
bugs by construction:

  * Try: a finally block is created only when finalbody is non-empty.
  * Return: no phantom block.  Control flow goes dead (current = None) and the
    return block is recorded in cfg.finalblocks, or wired through the innermost
    enclosing finally when there is one.

Every name below is kept so that codegate.analyzer imports keep working
unchanged.
"""

from __future__ import annotations

from pathlib import Path

from .cfg import (
    CFG,
    Block,
    CFGBuilder,
    Link,
    build_cfg,
    get_all_blocks_filtered,
)

__all__ = [
    "CFG",
    "Block",
    "Link",
    "CFGBuilder",
    "build_cfg",
    "build_cfg_from_file",
    "get_function_cfgs",
    "get_all_blocks_filtered",
    "iter_cfg_blocks",
    "apply_patches",
]


def apply_patches() -> None:
    """No-op kept for backwards compatibility.

    The Scalpel bugs are fixed by construction in codegate.cfg, so there is
    nothing left to monkey-patch.
    """
    return None


def build_cfg_from_file(path, name: str | None = None) -> CFG:
    """Build a CFG from a file on disk."""
    p = Path(path)
    return build_cfg(p.read_text(encoding="utf-8"), name or p.stem)


def get_function_cfgs(cfg: CFG) -> dict:
    """Return dict of (block_id, name) -> function CFG."""
    return dict(cfg.functioncfgs)


def iter_cfg_blocks(cfg: CFG):
    """Iterate blocks in BFS order, filtered."""
    yield from get_all_blocks_filtered(cfg)
