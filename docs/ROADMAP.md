# Remaining work

These are proposals, not implemented guarantees or promises of a release date.

- Design explicit dimensional units/conversions for points, vectors, and translation.
- Consider checked arithmetic for applications that require finite outputs after application/composition.
- Assess long-chain rotation drift and whether explicit reconditioning is needed.
- Add useful benchmarks before making any performance claims; current bench files are placeholders.
- Expand domain examples and populate diagrams where they explain a concrete workflow.
- Validate execution and timing on real embedded hardware; CI cross-compilation alone is insufficient.
- Define release/versioning and compatibility policy before the next published release.

Current behavior is specified in [requirements](requirements/requirements.md).
Completed work belongs in the [changelog](../CHANGELOG.md), not a stale checklist here.
