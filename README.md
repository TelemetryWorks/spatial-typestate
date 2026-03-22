<p align="center">
  <img src="https://raw.githubusercontent.com/TelemetryWorks/spatial-typestate/main/images/spatial_typestate_logo.png" alt="Spatial Typestate Banner" />
</p>

# Spatial Typestate

**Note:** This crate is currently a placeholder.

We have secured this name on `crates.io` while finalizing the initial version.

Please see the GitHub repository for current development status:
`https://github.com/TelemetryWorks/spatial-typestate`

|          |                                                                                                    |
|----------|----------------------------------------------------------------------------------------------------|
| License  | [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)                |

`spatial-typestate` is a Rust library for high-assurance 3D coordinate systems.  
  
It uses typestate to encode frame of reference and physical units in the type system so that frame mixups and unit errors can be caught at compile time instead of surfacing later at runtime.  

> **Warning**
> This library is intended to support rigorous engineering workflows, but it is not certified for safety-critical, life-critical, or mission-critical use. Users are responsible for independently verifying validation, suitability, and compliance for any deployment context.

## Status

This crate is under active development. Initial APIs, module layout, and documentation are still evolving.

## Development

See [CONTRIBUTING.md](https://github.com/TelemetryWorks/spatial-typestate/blob/main/CONTRIBUTING.md) for build, test, and contribution guidance.

## Requirements

Requirements are documented in [docs/requirements/requirements.md](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/requirements/requirements.md).

## Limitations & Alternatives

`spatial-typestate` is currently under heavy development. More details will be added in future versions.

## Additional Documentation

- [Project structure](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/PROJECT_STRUCTURE.md)
- [Safety notes](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/SAFETY.md)
- [Design notes](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/DESIGN.md)
- [Roadmap](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/ROADMAP.md)
