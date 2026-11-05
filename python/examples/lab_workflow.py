"""Offline analysis of SYNTHETIC 100 Hz sensor telemetry; stdlib + installed wheel.

CSV decoding is setup work. Coordinate conversion/mapping runs in Rust batches.
No live producer may mutate a buffer while it is imported.
"""
from array import array
import argparse
import csv
import json
import math
from pathlib import Path
import sys

from spatial_typestate import (
    DIMENSIONLESS, FEET, METERS, Frame, Points, Quaternion, SpatialError,
    Transform, Vectors,
)


def load_csv(path):
    """Decode explicit feet columns once; no guess about units/frame/calibration."""
    times, coordinates = array("d"), array("d")
    with Path(path).open(newline="", encoding="utf-8-sig") as source:
        rows = csv.reader(source)
        if next(rows, None) != ["time_s", "x_ft", "y_ft", "z_ft"]:
            raise ValueError("expected CSV header time_s,x_ft,y_ft,z_ft (feet)")
        for line, row in enumerate(rows, 2):
            if len(row) != 4:
                raise ValueError(f"CSV line {line}: expected four numeric columns")
            if any("_" in field for field in row):
                raise ValueError(f"CSV line {line}: underscores are not accepted in numbers")
            try:
                time, x, y, z = map(float, row)
            except ValueError as error:
                raise ValueError(f"CSV line {line}: invalid number") from error
            if not math.isfinite(time) or (times and time <= times[-1]):
                raise ValueError(f"CSV line {line}: times must be finite and increasing")
            times.append(time)
            coordinates.extend((x, y, z))
    if not times:
        raise ValueError("analysis needs at least one sample")
    return times, coordinates


def analyze(times, coordinates):
    """One import, explicit length conversion, composed map and inverse in Rust."""
    if not times or len(coordinates) != 3 * len(times):
        raise ValueError("one coordinate triple is required per timestamp")
    sensor, aircraft, world = Frame("Sensor"), Frame("Aircraft"), Frame("World")
    # Caller-supplied illustrative relationships, NOT physical calibration.
    sensor_aircraft = Transform.from_rotation_translation(
        sensor, aircraft, METERS, Quaternion(aircraft, 0., 0., 1., 1.), (1., 2., 3.))
    aircraft_world = Transform.from_rotation_translation(
        aircraft, world, METERS, Quaternion(world, 1., 0., 0., 1.), (10., 20., 30.))
    mapping = sensor_aircraft.then(aircraft_world)
    imported = Points.from_buffer(coordinates, sensor, FEET)
    meters = imported.convert_to(METERS)
    result = mapping.apply_points(meters)
    restored = mapping.inverse().apply_points(result)
    # Dimensionless sensor +x direction: rotations only, no translation.
    direction = Vectors.from_buffer(array("d", [1., 0., 0.]), sensor, DIMENSIONLESS)
    world_direction = mapping.apply_vectors(direction)
    view = result.view()  # One export; repeated view calls share cached bytes.
    first, last = tuple(view[:3]), tuple(view[-3:])
    report = {
        "data": "synthetic telemetry; not recorded or calibrated",
        "samples": len(result), "duration_s": times[-1] - times[0],
        "world_first_m": first, "world_last_m": last,
        "endpoint_displacement_m": math.dist(first, last),
        "world_sensor_x_direction": tuple(world_direction.view()),
    }
    return report, result, restored, mapping, sensor


def demonstrate_errors(mapping, sensor):
    """Real failures, no sentinel/partial result. Returns diagnostic descriptions."""
    diagnostics = []
    cases = [
        ("reuse the original Sensor frame", lambda: mapping.apply_points(
            Points.from_buffer(array("d", [0., 0., 0.]), Frame("Sensor"), METERS))),
        ("convert feet to meters explicitly", lambda: mapping.apply_points(
            Points.from_buffer(array("d", [0., 0., 0.]), sensor, FEET))),
        ("repair/reject nonfinite source row 1 before reimport", lambda: Points.from_buffer(
            array("d", [0., 0., 0., math.nan, 0., 0.]), sensor, METERS)),
    ]
    raw = [[sys.float_info.max, 0., 0., 0.], [0., 1., 0., 0.],
           [0., 0., 1., 0.], [0., 0., 0., 1.]]
    overflowing = Transform.from_matrix(sensor, mapping.target, METERS, raw)
    source = Points.from_buffer(array("d", [0., 0., 0., 2., 0., 0.]), sensor, METERS)
    # Fresh core conversion reads the Vec, rather than trusting cached export bytes.
    before = bytes(source.convert_to(METERS).view())
    cases.append(("inspect scale/range at row 1; no partial output was returned",
                  lambda: overflowing.apply_points(source)))
    for remedy, operation in cases:
        try:
            operation()
        except SpatialError as error:
            diagnostics.append(f"{error.code} index={error.index}: {remedy}")
        else:
            raise AssertionError("expected demonstration failure did not occur")
    if bytes(source.convert_to(METERS).view()) != before:
        raise AssertionError("failed apply changed the input")
    return diagnostics


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("data") / "synthetic_sensor_100hz.csv",
                        help="CSV with time_s,x_ft,y_ft,z_ft; default is SYNTHETIC")
    parser.add_argument("--demonstrate-errors", action="store_true")
    args = parser.parse_args(argv)
    try:
        times, coordinates = load_csv(args.input)
        report, _, _, mapping, sensor = analyze(times, coordinates)
        # User-supplied files have unknown provenance; do not label them recorded.
        if args.input != parser.get_default("input"):
            report["data"] = "input CSV; provenance caller-supplied; frame relationships are example illustrative constants, not calibration"
        print(json.dumps(report, indent=2, allow_nan=False))
        if args.demonstrate_errors:
            for diagnostic in demonstrate_errors(mapping, sensor):
                print(diagnostic)
    except SpatialError as error:
        location = f"row={error.index}"
        if error.index is not None:
            location += f" (CSV line={error.index + 2})"
        print(f"analysis failed: {error.code}, {location}: {error}; check frame, units and numeric range", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, BufferError, csv.Error) as error:
        print(f"analysis failed: {error}; check CSV schema and input data", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
