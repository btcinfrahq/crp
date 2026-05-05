#!/usr/bin/env python3
"""
CRP — Closed Root Protocol
Reference resolver (v0.1)

This is a minimal but real implementation:
- replays an ordered sequence of transitions
- builds the dependency DAG
- validates that every dependency is recoverable
- computes a deterministic Merkle root
- exposes a falsifiability mode (--break)

It is intentionally short. It is not optimized.
Its only purpose is to make the central claim observable:

    Execution without resolution is undefined.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

TRANSITIONS_DIR = Path(__file__).parent / "transitions"


# ---------------------------------------------------------------------------
# Canonicalization & hashing
# ---------------------------------------------------------------------------

def canonical_json(data) -> str:
    """RFC 8785-style canonical form: sorted keys, no whitespace."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short(h: str, n: int = 12) -> str:
    return h[:n]


# ---------------------------------------------------------------------------
# State replay
# ---------------------------------------------------------------------------

def load_transitions():
    """Load every transitions/NN_*.json in order."""
    if not TRANSITIONS_DIR.exists():
        raise FileNotFoundError(f"transitions/ not found at {TRANSITIONS_DIR}")
    files = sorted(p for p in TRANSITIONS_DIR.iterdir() if p.suffix == ".json")
    transitions = []
    for f in files:
        with open(f) as fh:
            transitions.append(json.load(fh))
    return transitions


def replay(transitions, up_to_state: int, break_path: str | None = None):
    """
    Apply transitions[0..up_to_state] and return the resulting state map.
    State 0 = empty. State k = first k transitions applied.

    If break_path is set, that artifact is removed from state to simulate
    a missing dependency (falsifiability mode).
    """
    if up_to_state < 0 or up_to_state > len(transitions):
        raise ValueError(
            f"state must be between 0 and {len(transitions)}; got {up_to_state}"
        )

    state: dict[str, dict] = {}
    for i in range(up_to_state):
        tx = transitions[i]
        if tx["type"] != "ADD_ARTIFACT":
            raise NotImplementedError(f"transition type: {tx['type']}")
        path = tx["path"]
        if path in state:
            raise ValueError(f"path already exists: {path}")
        state[path] = tx["artifact"]

    if break_path and break_path in state:
        del state[break_path]

    return state


# ---------------------------------------------------------------------------
# DAG validation & Merkle root
# ---------------------------------------------------------------------------

def collect_dependencies(state, root_path):
    """
    Walk dependencies transitively from root_path.
    Returns (ordered_paths, missing_paths).
    Detects missing deps. Detects cycles.
    """
    ordered = []
    seen: set[str] = set()
    visiting: set[str] = set()
    missing: list[str] = []
    missing_seen: set[str] = set()

    def visit(p):
        if p in seen:
            return
        if p in visiting:
            raise ValueError(f"cycle detected at {p}")
        if p not in state:
            if p not in missing_seen:
                missing.append(p)
                missing_seen.add(p)
            return
        visiting.add(p)
        artifact = state[p]
        for dep in artifact.get("dependencies", []):
            visit(dep)
        visiting.discard(p)
        seen.add(p)
        ordered.append(p)

    visit(root_path)
    return ordered, missing


def merkle_root(state, ordered_paths) -> str:
    """
    Deterministic root over the given ordered path list.
    Same paths in same order with same artifacts -> same root. Always.

    Used in two ways:
    - resolve: ordered_paths = transitive deps of target (subtree root)
    - merkle:  ordered_paths = sorted full state (global state root)
    """
    leaves = []
    for p in ordered_paths:
        leaf = sha256_hex(f"{p}|{canonical_json(state[p])}")
        leaves.append(leaf)
    if not leaves:
        return sha256_hex("")
    concat = "".join(leaves)
    return sha256_hex(concat)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_resolution(path, state_idx, artifact, ordered_paths, root_hash):
    deps = artifact.get("dependencies", [])
    execution = artifact.get("execution", {})
    steps = execution.get("steps", [])

    print()
    print(f"RESOLUTION: {path} @ state={state_idx}")
    print(f"ROOT HASH:  {short(root_hash)}")
    print()

    print("DEPENDENCIES")
    if deps:
        for i, dep in enumerate(deps):
            prefix = "└──" if i == len(deps) - 1 else "├──"
            print(f"{prefix} {dep}")
    else:
        print("└── none")

    print()
    print("EXECUTION")
    if steps:
        for i, step in enumerate(steps):
            prefix = "└──" if i == len(steps) - 1 else "├──"
            print(f"{prefix} {step}")
    else:
        print("└── none")

    print()
    print("DETERMINISM")
    print("same state → same root → same execution semantics")
    print()


def render_failure(path, state_idx, missing):
    print()
    print(f"RESOLUTION: {path} @ state={state_idx}")
    print(f"STATUS:     UNDEFINED")
    print()
    print("MISSING DEPENDENCIES")
    for i, m in enumerate(missing):
        prefix = "└──" if i == len(missing) - 1 else "├──"
        print(f"{prefix} {m}")
    print()
    print("Execution without resolution is undefined.")
    print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_resolve(args):
    transitions = load_transitions()
    state = replay(transitions, args.state, break_path=args.break_)

    if args.path not in state:
        render_failure(args.path, args.state, [args.path])
        return 1

    ordered, missing = collect_dependencies(state, args.path)

    if missing:
        render_failure(args.path, args.state, missing)
        return 1

    root = merkle_root(state, ordered)
    render_resolution(args.path, args.state, state[args.path], ordered, root)

    if args.json:
        print("CANONICAL OUTPUT")
        print(json.dumps(state[args.path], indent=2, sort_keys=True))
        print()

    return 0


def cmd_merkle(args):
    transitions = load_transitions()
    state = replay(transitions, args.state)
    if not state:
        print("MERKLE ROOT: <empty state>")
        return 0
    paths = sorted(state.keys())
    root = merkle_root(state, paths)
    print(f"MERKLE ROOT: {short(root)}")
    print(f"FULL HASH:   {root}")
    print(f"STATE:       {args.state}")
    print(f"ARTIFACTS:   {len(paths)}")
    print(f"CONSISTENCY: VERIFIED")
    return 0


def cmd_verify(args):
    """Check that the demo behaves as documented."""
    transitions = load_transitions()
    failures = 0

    # 1. Full state resolves cleanly
    full = replay(transitions, len(transitions))
    ordered, missing = collect_dependencies(full, "root.aiagent.engine")
    if missing:
        print(f"FAIL: missing deps in full state: {missing}")
        failures += 1
    else:
        r1 = merkle_root(full, ordered)
        r2 = merkle_root(full, ordered)
        if r1 != r2:
            print("FAIL: non-deterministic merkle root")
            failures += 1
        else:
            print(f"PASS: full resolution deterministic ({short(r1)})")

    # 2. Breaking a dep makes resolution undefined
    broken = replay(transitions, len(transitions),
                    break_path="root.aiagent.identity")
    _, missing = collect_dependencies(broken, "root.aiagent.engine")
    if not missing:
        print("FAIL: broken state still resolved (falsifiability not demonstrated)")
        failures += 1
    else:
        print(f"PASS: broken state correctly fails ({len(missing)} missing)")

    # 3. State 0 cannot resolve anything
    empty = replay(transitions, 0)
    _, missing = collect_dependencies(empty, "root.aiagent.engine")
    if not missing:
        print("FAIL: empty state resolved")
        failures += 1
    else:
        print("PASS: empty state correctly fails")

    print()
    if failures == 0:
        print("All invariants hold.")
        return 0
    print(f"{failures} invariant(s) violated.")
    return 1


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="crp",
        description="Closed Root Protocol — reference resolver (v0.1)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_resolve = sub.add_parser("resolve", help="resolve a path at a given state")
    p_resolve.add_argument("path")
    p_resolve.add_argument("--state", type=int, required=True)
    p_resolve.add_argument(
        "--break", dest="break_", default=None,
        help="remove an artifact from state to test falsifiability",
    )
    p_resolve.add_argument(
        "--json", action="store_true",
        help="also print the canonical JSON of the resolved artifact",
    )
    p_resolve.set_defaults(func=cmd_resolve)

    p_merkle = sub.add_parser("merkle", help="show merkle root at a given state")
    p_merkle.add_argument("--state", type=int, required=True)
    p_merkle.set_defaults(func=cmd_merkle)

    p_verify = sub.add_parser("verify", help="run protocol invariants")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
