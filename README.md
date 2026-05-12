# CRP — Closed Root Protocol

A reference implementation showing why a persistent identifier is not enough to make execution reproducible.

---

## Background

Naming systems on Bitcoin (BNS on Stacks, Ordinals-based names) solve routing: a name resolves to an address. They do not solve what happens when that address points to something whose meaning depends on prior state. If two parties reconstruct the state differently, they reach different conclusions about the same identifier.

CRP is a constraint that makes this reconstruction deterministic. Given an identifier and an ordered set of state transitions, resolution either produces a single canonical result or fails. There is no third option.

I built this after assembling a portfolio of `.btc` names and finding that the question of *what these names mean once resolved* had no clean answer in the existing tooling. CRP is the minimal constraint I could write down that makes the answer deterministic.

---

## Demo

    git clone <this-repo>
    cd <this-repo>
    python3 cli.py resolve root.aiagent.engine --state 3

Output:

    RESOLUTION: root.aiagent.engine @ state=3
    ROOT HASH:  163381f98ec8

    DEPENDENCIES
    ├── root.aiagent.identity
    └── root.aiagent.credential

    EXECUTION
    ├── validate_identity
    ├── verify_credentials
    └── execute_instruction_set

    DETERMINISM
    same state → same root → same execution semantics

The root hash is deterministic over `(path, canonical_json(artifact))` pairs in dependency order. Running the same command on the same state at any future point produces the same output.

---

## Falsifiability

The claim is testable. Remove a dependency, and resolution must fail — not silently degrade, not approximate, not guess.

    python3 cli.py resolve root.aiagent.engine --state 3 --break root.aiagent.identity

Output:

    RESOLUTION: root.aiagent.engine @ state=3
    STATUS:     UNDEFINED

    MISSING DEPENDENCIES
    └── root.aiagent.identity

    Execution without resolution is undefined.

Exit code: `1`.

The exit code is non-zero. A consumer of this resolver cannot proceed in ambiguity — it either gets a defined result or an explicit failure.

---

## Verify the invariants

    python3 cli.py verify

Three invariants are checked:

1. Full resolution is deterministic across replays.
2. Breaking any dependency makes resolution fail.
3. The empty state cannot resolve anything.

If any of these fail, the protocol claim is broken.

---

## Scope

Around 250 lines of Python, standard library only. State is built by replaying transitions in order from `transitions/`. Resolution walks the dependency DAG from a given path. The root hash is computed over `(path, canonical_json(artifact))` pairs in dependency order.

This is a reference implementation, not production software. It is not a token, not a routing layer (BNS and Ordinals already do that), and not an execution environment. CRP defines a constraint on how an execution layer must behave to be reproducible; building that layer is out of scope here.

---

## Mapping to `.btc` names

A `.btc` identifier becomes the entry point of a CRP path. Naming gives the entry. CRP gives the reconstructible meaning behind it.

| `.btc` name | CRP path |
| --- | --- |
| `aiagentidentity.btc` | `root.aiagent.identity` |
| `aiagentcredential.btc` | `root.aiagent.credential` |
| `aiagentengine.btc` | `root.aiagent.engine` |

See [`mapping.md`](./mapping.md) for the full table.

---

## Repository layout

    .
    ├── cli.py                    # the resolver
    ├── transitions/              # ordered state transitions (JSON)
    ├── expected-output/          # canonical outputs for verification
    ├── mapping.md                # .btc → CRP path mapping
    └── README.md

---

## Working Paper

Accompanies Working Paper N°002 — *Semantic Resolution* (BTC Infra HQ, 2026). Paper: [btcinfrahq.substack.com](https://btcinfrahq.substack.com), PDF in `paper/WP002.pdf`.

---

## Author

Antony Villetorte — BTC Infra HQ
[btcinfrahq.com](https://btcinfrahq.com)

---

## License

- Code: MIT
- Specification & paper: CC BY 4.0
