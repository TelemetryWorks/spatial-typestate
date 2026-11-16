# Development-dependency advisories — 2026-11-16

Owner assignment: security-first patch updates, cargo-deny CI and deliberate
Dependabot majors. Base: `914b594` (PR #36 merge). No release/settings/tag change.

## Reproduction and minimal lock delta

Cargo-deny 0.20.2 defaults reproduced two root-graph errors:
[RUSTSEC-2026-0204](https://rustsec.org/advisories/RUSTSEC-2026-0204.html)
(crossbeam-epoch through criterion/rayon) and
[RUSTSEC-2026-0097](https://rustsec.org/advisories/RUSTSEC-2026-0097.html)
(direct dev rand). Full-graph `unsound = "all"` additionally exposed
[RUSTSEC-2026-0486](https://rustsec.org/advisories/RUSTSEC-2026-0486.html)
(rustix through proptest/tempfile). All are dev-only here, not core runtime deps.

Targeted `cargo +1.99.0 update -p ... --precise ...` changes ONLY four root lock
package versions/checksums and their versioned dependency references:

| Package | Before | Patched |
| --- | --- | --- |
| crossbeam-epoch | 0.9.18 | 0.9.20 |
| rand (direct dev) | 0.8.5 | 0.8.6 |
| rand (transitive dev; same advisory) | 0.9.2 | 0.9.3 |
| rustix (newly exposed transitive unsound advisory) | 1.1.4 | 1.1.6 |

No packages or dependency edges are added/removed. Both Cargo manifests and the
native lock are byte-unchanged; the native graph contains none of these crates.
The native graph is still audited independently. The root normal-dependency tree
contains only spatial-typestate. Root lock hashing changes future Python source
identity; old C2/0.1.0 qualification is not evidence for this new tree.

## Shared policy and CI

Model: irig106-time main `38681fe2377f314e8041f85546eb0c11711b8a3b`,
[policy](https://github.com/TelemetryWorks/irig106-time/blob/38681fe2377f314e8041f85546eb0c11711b8a3b/deny.toml)
and [CI](https://github.com/TelemetryWorks/irig106-time/blob/38681fe2377f314e8041f85546eb0c11711b8a3b/.github/workflows/ci.yml).
Use SHA-pinned cargo-deny-action v2.1.1 (`3c6349835b2b7b196a839186cb8b78e02f7b5f25`),
whose Dockerfile selects cargo-deny 0.20.2. Explicit CI Rust is 1.99.0; two workers,
two matrix jobs maximum, read-only permissions, no checkout credentials.

The same policy denies vulnerabilities, ALL unsound/unmaintained advisories,
yanked versions, wildcard registry constraints and unknown external registries/git.
`ignore = []`. Internal reviewed core path dependencies remain allowed. Compared
with the reference, unsound checks explicitly include transitive dependencies.
The licence allowlist adds only the already-shipped native build dependency
`target-lexicon`'s `Apache-2.0 WITH LLVM-exception` expression to the reference's
permissive set. No licence files/declarations change; this is not legal certification.

`.github/deny.toml` is explicit in both jobs. A root-level config was seen in the
read-only package-list preview, so the final policy stays in the existing excluded
`.github` tree; neither packaging manifests nor sdist allowlists need relaxing.
The preview used `--allow-dirty --list` only, never package verification/signoff.

Every Dependabot entry keeps weekly scheduling, limit five and grouped minor/patch
updates. It adds only `dependency-name: "*"` plus
`version-update:semver-major` under `ignore`. Security updates are not disabled;
see [GitHub options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#ignore).
No existing PR is closed, auto-merged or exempted from checks.

## Validation boundary

On this cloud aarch64 host, official checksum-verified Rust 1.99.0 and cargo-deny
0.20.2 were used from isolated temporary homes, without reading existing credentials
or changing the project pin. Both locked, all-feature graphs pass advisories, bans,
licences and sources. Expected unused-licence/duplicate-version warnings are not
suppressed. Core default, no_std and all-feature test suites pass locally with two workers;
hosted exact-head required
checks, including Python packaging, remain separate evidence in the PR timeline.
No native runtime dependency or source/API change is included.
