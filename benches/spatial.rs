//! Runtime-input benchmarks; the executable uses std even for the no-std library.
#![deny(unsafe_code)]
#[path = "support/borrowed.rs"]
mod borrowed;
#[path = "support/experiments.rs"]
mod experiments;

use criterion::{
    BenchmarkGroup, Criterion, Throughput, criterion_group, criterion_main, measurement::WallTime,
};
use spatial_typestate::{
    Dimensionless, Feet, Frame, LengthUnit, LinearLengthUnit, Meters, Point3, Quantity, Transform,
    Unit, UnitQuat, Vector3,
};
use std::{hint::black_box, time::Duration};

struct World;
impl Frame for World {}
struct Sensor;
impl Frame for Sensor {}
struct Aircraft;
impl Frame for Aircraft {}
struct InvalidScale;
impl Unit for InvalidScale {}
impl LengthUnit for InvalidScale {}
impl LinearLengthUnit for InvalidScale {
    const METERS_PER_UNIT: f64 = 0.0;
}
struct Tiny;
impl Unit for Tiny {}
impl LengthUnit for Tiny {}
impl LinearLengthUnit for Tiny {
    const METERS_PER_UNIT: f64 = f64::from_bits(1);
}

const COUNT: usize = 64;
#[derive(Clone, Copy)]
struct Case {
    map: Transform<World, World, Meters>,
    next: Transform<World, World, Meters>,
    point: Point3<World, Meters>,
    rotation: UnitQuat<World>,
    components: [f64; 4],
}

fn cases(kind: &str) -> Vec<Case> {
    let mut state = std::env::var("SPATIAL_BENCH_SEED")
        .ok()
        .map_or(0x4d59_5df4_d0f3_3173, |s| {
            s.parse::<u64>().expect("u64 seed")
        });
    let mut number = || {
        state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1);
        f64::from(u32::try_from(state >> 32).unwrap()) / f64::from(u32::MAX) * 200.0 - 100.0
    };
    let mut error_state = 0x9e37_79b9_7f4a_7c15_u64;
    let length = if kind == "mixed_1in8" { 4096 } else { COUNT };
    (0..length)
        .map(|index| {
            let components = [number() / 100.0, number() / 100.0, number() / 100.0, 1.0];
            let mut case = Case {
                rotation: UnitQuat::try_from_components(
                    components[0],
                    components[1],
                    components[2],
                    components[3],
                )
                .unwrap(),
                components,
                map: Transform::from_matrix([
                    [0.8, -0.6, 0.0, number()],
                    [0.6, 0.8, 0.0, number()],
                    [0.0, 0.0, 1.0, number()],
                    [0.0, 0.0, 0.0, 1.0],
                ]),
                next: Transform::from_matrix([
                    [1.0, 0.0, 0.0, number()],
                    [0.0, 0.8, -0.6, number()],
                    [0.0, 0.6, 0.8, number()],
                    [0.0, 0.0, 0.0, 1.0],
                ]),
                point: Point3::new(number(), number(), number()),
            };
            error_state = error_state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1);
            match kind {
                "mixed_1in8" if error_state >> 61 == 0 => case.map.matrix[0][0] = f64::NAN,
                "late_nan" => case.map.matrix[2][2] = f64::NAN,
                "overflow" => {
                    case.point = Point3::new(f64::MAX, f64::MAX, f64::MAX);
                    for row in case.map.matrix.iter_mut().take(3) {
                        row[3] = f64::MAX;
                    }
                }
                "subnormal" => {
                    let tiny = f64::from_bits(1);
                    case.point = Point3::new(tiny, -tiny, 3.0 * tiny);
                    case.map.matrix = [
                        [0.5, tiny, 0.0, if index % 2 == 0 { 0.0 } else { tiny }],
                        [0.0, 0.5, 0.0, 0.0],
                        [0.0, 0.0, 0.5, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ];
                }
                _ => {}
            }
            case
        })
        .collect()
}

// Identical indexing/barriers for all independent-call comparisons. Selection
// overhead is measured separately, not subtracted from tiny timings.
fn indexed<T, R>(
    group: &mut BenchmarkGroup<'_, WallTime>,
    name: &str,
    data: &[T],
    mut operation: impl FnMut(&T) -> R,
) {
    group.bench_function(name, |b| {
        let mut index = 0;
        b.iter(|| {
            let input = black_box(&data[index]);
            index = (index + 1) & (data.len() - 1);
            black_box(operation(input))
        });
    });
}

fn operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("operations");
    for kind in ["valid", "mixed_1in8", "late_nan", "overflow", "subnormal"] {
        let data = cases(kind);
        indexed(&mut group, &format!("point_{kind}"), &data, |v| {
            black_box(&v.map).apply_point(black_box(v.point))
        });
        indexed(&mut group, &format!("vector_{kind}"), &data, |v| {
            black_box(&v.map).apply_vector(black_box(Vector3::<World, Dimensionless>::new(
                v.point.x, v.point.y, v.point.z,
            )))
        });
        indexed(&mut group, &format!("compose_{kind}"), &data, |v| {
            black_box(&v.map).then(black_box(v.next))
        });
        indexed(&mut group, &format!("inverse_{kind}"), &data, |v| {
            black_box(&v.map).try_inverse()
        });
    }
    let data = cases("valid");
    indexed(&mut group, "constructor_valid", &data, |v| {
        Transform::<World, World, Meters>::try_from_rotation_translation(
            black_box(v.rotation),
            black_box(Vector3::new(v.point.x, v.point.y, v.point.z)),
        )
    });
    indexed(&mut group, "normalize_construct_apply", &data, |v| {
        let [x, y, z, w] = black_box(v.components);
        let q = UnitQuat::try_from_components(x, y, z, w)?;
        let map = Transform::<World, World, Meters>::try_from_rotation_translation(
            q,
            black_box(Vector3::new(v.point.x, v.point.y, v.point.z)),
        )?;
        map.apply_point(black_box(v.point))
    });
    let mixed = cases("mixed_1in8");
    indexed(&mut group, "input_control_mixed", &mixed, |v| {
        black_box(v.point)
    });
    indexed(&mut group, "input_control", &data, |v| black_box(v.point));
    let mut nonrigid = data.clone();
    for v in &mut nonrigid {
        v.map.matrix[0][0] = 2.0;
    }
    indexed(&mut group, "inverse_nonrigid", &nonrigid, |v| {
        black_box(&v.map).try_inverse()
    });
    group.finish();
}

fn conversions(c: &mut Criterion) {
    let mut group = c.benchmark_group("conversion");
    for kind in ["valid", "overflow", "subnormal"] {
        let data = cases(kind);
        indexed(&mut group, &format!("quantity_{kind}"), &data, |v| {
            black_box(Quantity::<Meters>::new(v.point.x)).convert_to::<Feet>()
        });
        indexed(&mut group, &format!("point_{kind}"), &data, |v| {
            black_box(v.point).convert_to::<Feet>()
        });
        indexed(&mut group, &format!("vector_{kind}"), &data, |v| {
            black_box(Vector3::<World, Meters>::new(
                v.point.x, v.point.y, v.point.z,
            ))
            .convert_to::<Feet>()
        });
        indexed(&mut group, &format!("transform_{kind}"), &data, |v| {
            black_box(&v.map).convert_to::<Feet>()
        });
    }
    let subnormal = cases("subnormal");
    indexed(&mut group, "point_shrink_subnormal", &subnormal, |v| {
        black_box(Point3::<World, Feet>::new(v.point.x, v.point.y, v.point.z))
            .convert_to::<Meters>()
    });
    let mut data = cases("valid");
    for v in &mut data {
        v.point.x = f64::NAN;
    }
    indexed(&mut group, "quantity_nan", &data, |v| {
        black_box(Quantity::<Meters>::new(v.point.x)).convert_to::<Feet>()
    });
    indexed(&mut group, "metadata_error", &data, |v| {
        black_box(Quantity::<InvalidScale>::new(v.point.x)).convert_to::<Meters>()
    });
    indexed(&mut group, "factor_error", &data, |v| {
        black_box(Quantity::<Meters>::new(v.point.x)).convert_to::<Tiny>()
    });
    let data = cases("valid");
    indexed(&mut group, "point_same_unit", &data, |v| {
        black_box(v.point).convert_to::<Meters>()
    });
    group.finish();
}

fn point_candidates(c: &mut Criterion) {
    let mut group = c.benchmark_group("point_candidates");
    let order = if std::env::var_os("SPATIAL_BENCH_REVERSE").is_some() {
        [2, 1, 0]
    } else {
        [0, 1, 2]
    };
    for kind in ["valid", "mixed_1in8", "late_nan", "overflow", "subnormal"] {
        let data = cases(kind);
        for candidate in order {
            match candidate {
                0 => indexed(&mut group, &format!("{kind}/baseline"), &data, |v| {
                    black_box(&v.map).apply_point(black_box(v.point))
                }),
                1 => indexed(&mut group, &format!("{kind}/eager"), &data, |v| {
                    experiments::point_eager(black_box(&v.map), black_box(v.point))
                }),
                _ => indexed(&mut group, &format!("{kind}/rows"), &data, |v| {
                    experiments::point_rows(black_box(&v.map), black_box(v.point))
                }),
            }
        }
    }
    group.finish();
}

fn quaternions(c: &mut Criterion) {
    let mut group = c.benchmark_group("quaternion");
    for kind in ["normal", "near_unit", "extreme", "error"] {
        let values: Vec<_> = cases("valid")
            .iter()
            .enumerate()
            .map(|(i, v)| match kind {
                "near_unit" => [
                    v.rotation.x(),
                    v.rotation.y(),
                    v.rotation.z(),
                    v.rotation.w(),
                ],
                "extreme" if i % 2 == 0 => [f64::MAX, -f64::MAX, 1.0, -0.0],
                "extreme" => [
                    f64::from_bits(1),
                    -f64::from_bits(2),
                    0.0,
                    f64::from_bits(3),
                ],
                "error" if i % 2 == 0 => [f64::NAN, 0.0, 0.0, 1.0],
                "error" => [0.0; 4],
                _ => [v.point.x, v.point.y, v.point.z, 1.0],
            })
            .collect();
        let order = if std::env::var_os("SPATIAL_BENCH_REVERSE").is_some() {
            [2, 1, 0]
        } else {
            [0, 1, 2]
        };
        for candidate in order {
            match candidate {
                0 => indexed(&mut group, &format!("{kind}/public"), &values, |v| {
                    let [x, y, z, w] = black_box(*v);
                    UnitQuat::<World>::try_from_components(x, y, z, w)
                }),
                1 => indexed(&mut group, &format!("{kind}/replay8"), &values, |v| {
                    experiments::normalize_steps::<8>(black_box(*v))
                }),
                _ => indexed(&mut group, &format!("{kind}/replay6"), &values, |v| {
                    experiments::normalize_steps::<6>(black_box(*v))
                }),
            }
        }
    }
    group.finish();
}

fn workflows(c: &mut Criterion) {
    let data = cases("valid");
    let first = Transform::<Sensor, Aircraft, Meters>::from_matrix(data[0].map.matrix);
    let next = Transform::<Aircraft, World, Meters>::from_matrix(data[0].next.matrix);
    let input: Vec<_> = data
        .iter()
        .map(|v| Point3::<Sensor, Meters>::new(v.point.x, v.point.y, v.point.z))
        .collect();
    let (xs, ys, zs): (Vec<_>, Vec<_>, Vec<_>) = (
        input.iter().map(|p| p.x).collect(),
        input.iter().map(|p| p.y).collect(),
        input.iter().map(|p| p.z).collect(),
    );
    let mut out = [Point3::<World, Feet>::new(0.0, 0.0, 0.0); COUNT];
    let mut group = c.benchmark_group("workflow");
    group.throughput(Throughput::Elements(COUNT as u64));
    group.bench_function("sequential_batch64", |b| {
        b.iter(|| {
            let (first, next, input) = black_box((&first, &next, &input));
            for (output, point) in out.iter_mut().zip(input) {
                *output = next
                    .apply_point(first.apply_point(*point).unwrap())
                    .unwrap()
                    .convert_to::<Feet>()
                    .unwrap();
            }
            black_box(&out);
        })
    });
    group.bench_function("compose_each_batch64", |b| {
        b.iter(|| {
            let (first, next, input) = black_box((&first, next, &input));
            let composed = first.then(next).unwrap();
            for (output, point) in out.iter_mut().zip(input) {
                *output = composed
                    .apply_point(*point)
                    .unwrap()
                    .convert_to::<Feet>()
                    .unwrap();
            }
            black_box(&out);
        })
    });
    group.bench_function("soa_compose_each_batch64", |b| {
        b.iter(|| {
            let (first, next, xs, ys, zs) = black_box((&first, next, &xs, &ys, &zs));
            let composed = first.then(next).unwrap();
            for (i, output) in out.iter_mut().enumerate() {
                *output = composed
                    .apply_point(Point3::new(xs[i], ys[i], zs[i]))
                    .unwrap()
                    .convert_to::<Feet>()
                    .unwrap();
            }
            black_box(&out);
        })
    });
    group.bench_function("dependent_chain64", |b| {
        b.iter(|| {
            let (map, mut point) = black_box((&data[0].map, data[0].point));
            for _ in 0..COUNT {
                point = map.apply_point(point).unwrap();
            }
            black_box(point)
        })
    });
    group.finish();
}

fn preparation(c: &mut Criterion) {
    let data = cases("valid");
    let mut group = c.benchmark_group("preparation");
    indexed(&mut group, "prepare_only", &data, |v| {
        experiments::Prepared::new(black_box(v.map))
    });
    indexed(&mut group, "prepare_each_point", &data, |v| {
        experiments::Prepared::new(black_box(v.map))
            .unwrap()
            .apply(black_box(v.point))
    });
    group.throughput(Throughput::Elements(COUNT as u64));
    let map = data[0].map;
    let prepared = experiments::Prepared::new(map).unwrap();
    let points: Vec<_> = data.iter().map(|v| v.point).collect();
    let mut out = [Point3::<World, Meters>::new(0.0, 0.0, 0.0); COUNT];
    group.bench_function("checked_batch64", |b| {
        b.iter(|| {
            let (map, points) = black_box((&map, &points));
            for (output, point) in out.iter_mut().zip(points) {
                *output = map.apply_point(*point).unwrap();
            }
            black_box(&out);
        })
    });
    group.bench_function("prepared_reuse_batch64", |b| {
        b.iter(|| {
            let (prepared, points) = black_box((&prepared, &points));
            for (output, point) in out.iter_mut().zip(points) {
                *output = prepared.apply(*point).unwrap();
            }
            black_box(&out);
        })
    });
    group.bench_function("prepare_each_batch64", |b| {
        b.iter(|| {
            let (map, points) = black_box((map, &points));
            let prepared = experiments::Prepared::new(map).unwrap();
            for (output, point) in out.iter_mut().zip(points) {
                *output = prepared.apply(*point).unwrap();
            }
            black_box(&out);
        })
    });
    group.finish();
}

fn configuration() -> Criterion {
    Criterion::default()
        .sample_size(40)
        .warm_up_time(Duration::from_millis(200))
        .measurement_time(Duration::from_millis(700))
        .nresamples(10_000)
        .noise_threshold(0.03)
}

fn controls(c: &mut Criterion) {
    let mut group = c.benchmark_group("controls");
    let reverse = std::env::var_os("SPATIAL_BENCH_REVERSE").is_some();
    let order = if reverse { [2, 1, 0] } else { [0, 1, 2] };
    for kind in ["valid", "subnormal"] {
        let data = cases(kind);
        for candidate in order {
            match candidate {
                0 => indexed(&mut group, &format!("single_{kind}/public"), &data, |v| {
                    black_box(&v.map).apply_point(black_box(v.point))
                }),
                1 => indexed(&mut group, &format!("single_{kind}/local"), &data, |v| {
                    experiments::point_local(black_box(&v.map), black_box(v.point))
                }),
                _ => indexed(&mut group, &format!("single_{kind}/forced"), &data, |v| {
                    experiments::point_forced(black_box(&v.map), black_box(v.point))
                }),
            }
        }
    }
    let data = cases("valid");
    let map = data[0].map;
    let prepared = experiments::Prepared::new(map).unwrap();
    let points: Vec<_> = data.iter().map(|v| v.point).collect();
    let mut out = [Point3::<World, Meters>::new(0.0, 0.0, 0.0); COUNT];
    group.throughput(Throughput::Elements(COUNT as u64));
    let order = if reverse { [3, 2, 1, 0] } else { [0, 1, 2, 3] };
    for candidate in order {
        match candidate {
            0 => {
                group.bench_function("batch_public64", |b| {
                    b.iter(|| {
                        let (map, points) = black_box((&map, &points));
                        for (out, p) in out.iter_mut().zip(points) {
                            *out = map.apply_point(*p).unwrap();
                        }
                        black_box(&out);
                    })
                });
            }
            1 => {
                group.bench_function("batch_local64", |b| {
                    b.iter(|| {
                        let (map, points) = black_box((&map, &points));
                        for (out, p) in out.iter_mut().zip(points) {
                            *out = experiments::point_local(map, *p).unwrap();
                        }
                        black_box(&out);
                    })
                });
            }
            2 => {
                group.bench_function("batch_forced64", |b| {
                    b.iter(|| {
                        let (map, points) = black_box((&map, &points));
                        for (out, p) in out.iter_mut().zip(points) {
                            *out = experiments::point_forced(map, *p).unwrap();
                        }
                        black_box(&out);
                    })
                });
            }
            _ => {
                group.bench_function("batch_prepared64", |b| {
                    b.iter(|| {
                        let (map, points) = black_box((&prepared, &points));
                        for (out, p) in out.iter_mut().zip(points) {
                            *out = map.apply(*p).unwrap();
                        }
                        black_box(&out);
                    })
                });
            }
        }
    }
    group.finish();
}

fn amortization(c: &mut Criterion) {
    let data = cases("valid");
    let ordinary = data[0].map;
    let mut group = c.benchmark_group("amortization");
    let reverse = std::env::var_os("SPATIAL_BENCH_REVERSE").is_some();
    for (kind, n) in [
        ("valid", 1_usize),
        ("valid", 8),
        ("valid", 64),
        ("valid", 1024),
        ("subnormal", 64),
        ("mixed_nan", 64),
        ("overflow", 64),
    ] {
        let mut map = ordinary;
        if kind == "subnormal" {
            map.matrix = [
                [0.5, f64::from_bits(1), 0.0, 0.0],
                [0.0, 0.5, 0.0, 0.0],
                [0.0, 0.0, 0.5, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ];
        }
        if kind == "overflow" {
            for row in map.matrix.iter_mut().take(3) {
                row[3] = f64::MAX;
            }
        }
        let mut state = 0x8e45_a4b7_32cd_9f01_u64;
        let points: Vec<_> = (0..n)
            .map(|i| {
                let base = data[i % COUNT].point;
                state = state
                    .wrapping_mul(6_364_136_223_846_793_005)
                    .wrapping_add(1);
                match kind {
                    "subnormal" => {
                        Point3::new(f64::from_bits(1), -f64::from_bits(1), f64::from_bits(3))
                    }
                    "mixed_nan" if state >> 61 == 0 => Point3::new(f64::NAN, base.y, base.z),
                    "overflow" => Point3::new(f64::MAX, f64::MAX, f64::MAX),
                    _ => base,
                }
            })
            .collect();
        let prepared = borrowed::BorrowedPoint::prepare(&map).unwrap();
        let mut outputs = vec![Err(spatial_typestate::SpatialError::NonFinite); n];
        group.throughput(Throughput::Elements(n as u64));
        let order = if reverse {
            [4, 3, 2, 1, 0]
        } else {
            [0, 1, 2, 3, 4]
        };
        for variant in order {
            let prefix = format!("point_{kind}_n{n}");
            match variant {
                0 => {
                    group.bench_function(format!("{prefix}/public"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&map, &points[..], &mut outputs[..]));
                            assert_eq!(input.len(), output.len());
                            for (out, p) in output.iter_mut().zip(input) {
                                *out = map.apply_point(*p);
                            }
                            black_box(output);
                        })
                    });
                }
                1 => {
                    group.bench_function(format!("{prefix}/full_local"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&map, &points[..], &mut outputs[..]));
                            assert_eq!(input.len(), output.len());
                            for (out, p) in output.iter_mut().zip(input) {
                                *out = experiments::point_local(map, *p);
                            }
                            black_box(output);
                        })
                    });
                }
                2 => {
                    group.bench_function(format!("{prefix}/caller_hoisted"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&map, &points[..], &mut outputs[..]));
                            borrowed::caller_local_points(map, input, output).unwrap();
                            black_box(output);
                        })
                    });
                }
                3 => {
                    group.bench_function(format!("{prefix}/prepare_each_batch"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&map, &points[..], &mut outputs[..]));
                            assert_eq!(input.len(), output.len());
                            let prepared = borrowed::BorrowedPoint::prepare(map).unwrap();
                            for (out, p) in output.iter_mut().zip(input) {
                                *out = prepared.apply_point(*p);
                            }
                            black_box(output);
                        })
                    });
                }
                _ => {
                    group.bench_function(format!("{prefix}/borrowed_reuse"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&prepared, &points[..], &mut outputs[..]));
                            assert_eq!(input.len(), output.len());
                            for (out, p) in output.iter_mut().zip(input) {
                                *out = map.apply_point(*p);
                            }
                            black_box(output);
                        })
                    });
                }
            }
        }
    }
    for kind in ["valid", "ignored_translation"] {
        let mut map = ordinary;
        if kind == "ignored_translation" {
            map.matrix[0][3] = f64::NAN;
            map.matrix[1][3] = f64::INFINITY;
            map.matrix[3] = [f64::NAN; 4];
        }
        let vectors: Vec<_> = data
            .iter()
            .map(|v| Vector3::<World, Dimensionless>::new(v.point.x, v.point.y, v.point.z))
            .collect();
        let prepared = borrowed::BorrowedVector::prepare(&map).unwrap();
        let mut outputs = vec![Err(spatial_typestate::SpatialError::NonFinite); COUNT];
        group.throughput(Throughput::Elements(COUNT as u64));
        let order = if reverse { [3, 2, 1, 0] } else { [0, 1, 2, 3] };
        for variant in order {
            match variant {
                0 => {
                    group.bench_function(format!("vector_{kind}_n64/public"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&map, &vectors[..], &mut outputs[..]));
                            assert_eq!(input.len(), output.len());
                            for (out, v) in output.iter_mut().zip(input) {
                                *out = map.apply_vector(*v);
                            }
                            black_box(output);
                        })
                    });
                }
                1 => {
                    group.bench_function(format!("vector_{kind}_n64/caller_hoisted"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&map, &vectors[..], &mut outputs[..]));
                            borrowed::caller_local_vectors(map, input, output).unwrap();
                            black_box(output);
                        })
                    });
                }
                2 => {
                    group.bench_function(format!("vector_{kind}_n64/prepare_each_batch"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&map, &vectors[..], &mut outputs[..]));
                            assert_eq!(input.len(), output.len());
                            let prepared = borrowed::BorrowedVector::prepare(map).unwrap();
                            for (out, v) in output.iter_mut().zip(input) {
                                *out = prepared.apply_vector(*v);
                            }
                            black_box(output);
                        })
                    });
                }
                _ => {
                    group.bench_function(format!("vector_{kind}_n64/borrowed_reuse"), |b| {
                        b.iter(|| {
                            let (map, input, output) =
                                black_box((&prepared, &vectors[..], &mut outputs[..]));
                            assert_eq!(input.len(), output.len());
                            for (out, v) in output.iter_mut().zip(input) {
                                *out = map.apply_vector(*v);
                            }
                            black_box(output);
                        })
                    });
                }
            }
        }
    }
    group.finish();
    let mut group = c.benchmark_group("amortization_setup");
    group.bench_function("point_valid", |b| {
        b.iter(|| black_box(borrowed::BorrowedPoint::prepare(black_box(&ordinary))))
    });
    group.bench_function("vector_valid", |b| {
        b.iter(|| black_box(borrowed::BorrowedVector::prepare(black_box(&ordinary))))
    });
    let mut bad_translation = ordinary;
    bad_translation.matrix[0][3] = f64::NAN;
    group.bench_function("point_bad_translation", |b| {
        b.iter(|| {
            black_box(borrowed::BorrowedPoint::prepare(black_box(
                &bad_translation,
            )))
        })
    });
    let mut bad_linear = ordinary;
    bad_linear.matrix[2][2] = f64::NAN;
    group.bench_function("vector_bad_linear", |b| {
        b.iter(|| black_box(borrowed::BorrowedVector::prepare(black_box(&bad_linear))))
    });
    group.finish();
}
criterion_group! {name=benches;config=configuration();targets=operations,conversions,point_candidates,quaternions,workflows,preparation,controls,amortization}
criterion_main!(benches);
