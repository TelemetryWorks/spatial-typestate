# Spatial Typestate for Python

Published [0.1.0](https://pypi.org/project/spatial-typestate/0.1.0/), checked on
2026-11-09: batch-oriented CPython binding with no runtime Python dependencies.
The distribution is `spatial-typestate`, the import is `spatial_typestate`, and
the extension is `spatial_typestate._native`.

In a virtual environment with GIL-enabled CPython >=3.11,<3.15:

```sh
python -m pip install --only-binary=:all: spatial-typestate==0.1.0
```

Wheels: Windows x86_64 (`cp311-abi3-win_amd64`) and Linux x86_64
(`cp311-abi3-manylinux_2_28_x86_64`, glibc >=2.28). The same selected wheels were
qualified on CPython 3.11/3.14, with Linux glibc 2.28/2.36 container checks.
3.12/3.13 are metadata-compatible, not in the CI matrix; local Windows 3.12 is
additional evidence. No macOS, musl, ARM, PyPy or free-threaded claim. Wheel-only
install fails on an unsupported platform; ordinary pip may build the sdist and
needs an installed Rust toolchain and platform build tools.

The release embeds source C2 `9974fd6a00521d631d6ff6e35d4aa936f6b624cf`;
`python-v0.1.0` and `rust-v0.1.0` both point there and must never move.
Rust/Python versions evolve independently. The private native crate is not a
separate published Rust package. See the
[first-release limits and Rust migration](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/migration-0.0.1-to-0.1.0.md)
and [guide](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/PYTHON-GUIDE.md)
for copies, runtime checks and guarantees lost at the Python boundary.

Python 0.1.0 was token-uploaded without public PyPI attestations. Embedded source
records do not provide signed PyPI provenance. All future uploads require
[Trusted Publishing and per-file PEP 740 attestations](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/RELEASING.md#mandatory-future-pypi-publishing-policy).
This repository description is corrected for future packaging; the already
published 0.1.0 description still says unpublished candidate and cannot be fixed
by changing this file. No artifact replacement or re-upload is permitted.
