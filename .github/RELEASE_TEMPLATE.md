# AI Forensics vX.Y.Z Release Notes

**Release Date:** YYYY-MM-DD
**Git Tag:** `vX.Y.Z`

---

## What's New

<!-- Fill this out per release -->
- New model format scanner: `.onnx`
- Improved pickle inspection heuristics
- Added test coverage for entropy scanner
- SBOM generation now includes SPDX format

See the full changelog in [CHANGELOG.md](./CHANGELOG.md)

---

## Container Image

- `ghcr.io/TelemetryWorks/spatial-typestate:vX.Y.Z`
- `ghcr.io/TelemetryWorks/spatial-typestate:latest` (stable alias)

```bash
docker pull ghcr.io/TelemetryWorks/spatial-typestate:vX.Y.Z
```

## Digital Signature

This release is signed using [Cosign](https://docs.sigstore.dev/cosign/).
To verify:
```bash
cosign verify --key cosign.pub ghcr.io/TelemetryWorks/spatial-typestate:vX.Y.Z
```
- Public key: `[cosign.pub](https://raw.githubusercontent.com/TelemetryWorks/spatial-typestate/main/keys/cosign.pub)`
- Fingerprint: `SHA256: abcdef...`

## Code Quality & Security

-
-
Static analysis and quality gates are enforced by [SonarCloud](https://sonarcloud.io/).

## SBOM and Metadata

The following artifacts are published with this release:

| Artifact              | Description                            |
| --------------------- | -------------------------------------- |
| `release.md`          | Signed release summary (Markdown)      |
| `release.html`        | Human-readable signed summary          |
| `release.html.asc`    | ASCII-armored GPG signature            |
| `sbom.cyclonedx.json` | Software Bill of Materials (CycloneDX) |
| `sbom.spdx.json`      | Software Bill of Materials (SPDX)      |

## How to Verify This Release

```bash
# Verify container image signature
cosign verify --key cosign.pub ghcr.io/TelemetryWorks/spatial-typestate:vX.Y.Z

# Verify HTML release file
gpg --verify release.html.asc release.html
```

## Documentation

- [Security Policy](./SECURITY.md)
- [Workflow Overview](./docs/development/WORKFLOWS.md)
- [Contribution Guide](./CONTRIBUTING.md)