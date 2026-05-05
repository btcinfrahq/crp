# CRP — Closed Root Protocol

**Persistence is solved. Execution is not.**

Identifiers persist.
Meaning drifts.
Execution breaks silently.

---

## The claim

An asset is only truly executable if its meaning can be reconstructed
from state alone, without external assumptions.

Most systems solve **routing**: identifier → address.
None solve **resolution**: identifier → executable meaning.

CRP is the minimal constraint that forces the second.

---

## Demo

```bash
git clone <this-repo>
cd <this-repo>
python3 cli.py resolve root.aiagent.engine --state 3
```

Output:

```
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
```

Same state, same root. Always. Run it twice. Run it tomorrow. Run it in 2035.

---

## Falsifiability

The claim is testable. Remove a dependency, and resolution must fail —
not silently degrade, not approximate, not guess.

```bash
python3 cli.py resolve root.aiagent.engine --state 3 --break root.aiagent.identity
```

Output:

```
RESOLUTION: root.aiagent.engine @ state=3
STATUS:     UNDEFINED

MISSING DEPENDENCIES
└── root.aiagent.identity

Execution without resolution is undefined.
```

Exit code: `1`.

This is the protocol property: **a single missing dependency makes
execution undefined, observably and immediately.**

---

## Verify the invariants

```bash
python3 cli.py verify
```

Three invariants are checked:

1. Full resolution is deterministic across replays.
2. Breaking any dependency makes resolution fail.
3. The empty state cannot resolve anything.

If any of these fail, the protocol claim is broken.

---

## What this is

A reference implementation in ~250 lines of Python. No dependencies
beyond the standard library. The transitions are plain JSON files
under `transitions/`.

State is built by replaying transitions in order. Resolution walks
the dependency DAG from a given path. The root hash is deterministic
over `(path, canonical_json(artifact))` pairs in dependency order.

This is not production software. It exists to make a property
observable.

---

## What this is not

- Not a token, not a product, not a service.
- Not a routing layer (that is what naming systems already do).
- Not a virtual machine. CRP defines the constraint that makes
  any execution layer reproducible — it does not replace one.

---

## Mapping to `.btc` names

A `.btc` identifier becomes the entry point of a CRP path.
Naming gives the entry. CRP gives the reconstructible meaning behind it.

| `.btc` name             | CRP path                    |
|-------------------------|-----------------------------|
| `aiagentidentity.btc`   | `root.aiagent.identity`     |
| `aiagentcredential.btc` | `root.aiagent.credential`   |
| `aiagentengine.btc`     | `root.aiagent.engine`       |

See [`mapping.md`](mapping.md) for the full table.

---

## Repository layout

```
.
├── cli.py                    # the resolver
├── transitions/              # ordered state transitions (JSON)
├── expected-output/          # canonical outputs for verification
├── mapping.md                # .btc → CRP path mapping
└── README.md
```

---

## Working Paper

This implementation accompanies:

> **Working Paper N°002 — Semantic Resolution**
> *Execution without resolution is undefined.*
> BTC Infra HQ, 2026.

Paper: [btcinfrahq.substack.com](https://btcinfrahq.substack.com)
PDF: `paper/WP002.pdf`

---

## License

- Code: MIT
- Specification & paper: CC BY 4.0

---

> Persistence secures existence.
> Resolution secures usability.
>
> **Execution without resolution is undefined.**
