# Synthetic telemetry lab walkthrough

This executable offline analysis models a sensor mounted on an aircraft, with
coordinates reported in a world frame. It uses the existing installed Python
wheel and the standard library. It is **deterministic synthetic telemetry**,
not recorded lab/flight data, measured calibration, an accuracy claim or a
certification example. No performance measurements are added here.

## Data and physical assumptions

No recorded data or private source metadata is used or redistributed.
The existing Rust sensor_alignment example grounds the two-quarter-turn setup.

[The synthetic CSV](../python/examples/data/synthetic_sensor_100hz.csv) contains
201 samples over 2 seconds at 100 Hz: row i has time i/100 seconds and sensor-frame
coordinates (30+0.02i, -2+0.005i, 3+0.001i) **international feet**. It represents
a short smooth target track; it is not a model of sensor noise or aircraft dynamics.
The name and this document are its provenance; the CSV header declares units.

The application supplies these constant illustrative frame relationships:

1. Sensor -> Aircraft: right-handed +90 degrees about z, then target-frame
   translation (1,2,3) meters. Thus (x,y,z) -> (-y+1,x+2,z+3).
2. Aircraft -> World: right-handed +90 degrees about x, then world translation
   (10,20,30) meters. Thus (a,b,c) -> (a+10,-c+20,b+30).

After feet-to-meters conversion the independent combined oracle is
**(11-0.3048y_ft, 17-0.3048z_ft, 32+0.3048x_ft)**. Expected endpoints are
(11.6096,16.0856,41.144) and (11.3048,16.02464,42.3632) meters. Sensor +x as a
dimensionless direction becomes world (0,0,1); translations do not participate.
Tests compare every coordinate and the inverse roundtrip at absolute 1e-10 meters
for this bounded data, and directions at 1e-12. These tolerances are example-specific,
not universal error bounds. Swapping transforms, signs or units changes the oracle.

These are caller assertions about axes, units and physical mounting, not facts
inferred by runtime tags. Create each Frame once and share it: another
Frame("Sensor") is a different identity. No global frame-name registry exists.

## Run against an installed wheel

Build/install as in [the Python guide](PYTHON-GUIDE.md). From PowerShell, use
absolute paths and run outside the checkout, with isolation enabled:

```powershell
$python = (Resolve-Path target/python-venv/Scripts/python.exe).Path
$example = (Resolve-Path python/examples/lab_workflow.py).Path
Push-Location $env:TEMP
try {
    & $python -I $example --help
    & $python -I $example --demonstrate-errors
} finally { Pop-Location }
```

The script/fixture are repository examples, not installed console commands or
wheel resources. They import spatial_typestate from the installed wheel; no
sys.path adjustment or source package import is used. JSON output includes sample
count, duration, endpoint coordinates, displacement and a rotated direction.
Last-bit decimal output may vary by platform; the numerical assertions use the
stated tolerances, not a frozen text snapshot. Supply --input path/to/file.csv to
analyze the same explicit schema/units; you are responsible for provenance and
checking the example's fixed illustrative frame relationships; no calibration
is loaded from the CSV. UTF-8 with or without a BOM is accepted. Numeric underscores are rejected
rather than interpreted as digit separators. Timestamps must be finite/increasing; coordinates
must be finite at import. This is a constant-pose example, not pose interpolation,
clock synchronization, a Chapter 10 decoder, live acquisition or data cleaning.

## Where work and objects live

CSV parsing builds one array('d') of timestamps and one flat coordinate array
during setup. Python decoding necessarily creates temporary scalars per CSV row;
this is not the numeric hot path. Coordinates are imported **once** into one Rust
Points batch in feet. Explicit convert_to(METERS), composition, point application,
inverse application and vector mapping use Rust loops/core checked operations,
without Python row callbacks, per-point classes, tuples or dictionaries.
The Python summary reads only two endpoint triples; it does not loop over samples.
The independent test oracle loops in Python solely for verification.

Import copies the source coordinate payload once. Conversion, mapping and inverse
each allocate a new Rust payload. First result.view() copies once to cached immutable
bytes, plus zero fill; subsequent views share it. Inside analyze, the source array,
feet Vec, meter Vec, world Vec, restored Vec and world bytes can coexist: roughly
six coordinate payloads, plus timestamps, the small direction batch/export and
allocator/metadata overhead. Returned values retain world/restored Vec and world
bytes; temporary feet/meter batches can drop. This is not zero-copy or a measured
peak-memory bound. The view is read-only and can outlive its batch, but does not
encode a Rust lifetime. Stop native/external writers during buffer import.

## Errors a lab caller must handle

--demonstrate-errors performs actual failing calls and prints corrective guidance:

- FrameMismatch, index=None: a fresh same-name Frame is not the shared Sensor.
- UnitMismatch, index=None: mapping meters requires explicit conversion from feet.
- NonFinite, index=1 at import: repair/reject the second source row, then reimport.
- NonFinite, index=1 during mapping: a finite extreme raw scale overflows on the
  second row. Inspect range/scale; no partial result is returned. Fresh checked
  conversions read back the Rust-owned input before/after the failed call to
  verify it remains intact, without reusing cached export bytes.

Rows are zero-based, first failure ascending; coordinate row N corresponds to
CSV line N+2 (one header line). Mapping is all-or-nothing, not a
partial-output or NaN-sentinel pipeline. Import errors occur before mapping.
Malformed CSV/file errors or SpatialError print an actionable stderr message,
return exit code 2 and publish no summary; unexpected programming errors retain
their traceback. Real applications should log source row/timestamp and choose an
explicit reject/repair policy, rather than silently drop rows or reinterpret units.

Python loses Rust compile-time frame/unit checks, generic custom markers and
no_std execution; runtime identities and closed units replace only a subset.
Physical calibration, dimensional correctness of raw coefficients and data truth
remain caller responsibilities. See the complete [contract/copy/loss table](PYTHON-GUIDE.md),
[release policy](RELEASING.md) and [example tests](../python/tests/test_lab_workflow.py).
