"""Installed-wheel contract tests using only the Python standard library."""
import array
import concurrent.futures
import copy
import ctypes
import gc
import importlib.resources
import math
import pickle
from pathlib import Path
import re
import struct
import sys
import unittest

from spatial_typestate import (
    DIMENSIONLESS, FEET, METERS, Frame, Points, Quaternion, SpatialError, Transform,
    Unit, Vectors,
)

try:
    import numpy as np
except ImportError:
    np = None

ID = [[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]]


def triples(values):
    return array.array("d", values)


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b, self.c = Frame("Sensor"), Frame("Aircraft"), Frame("World")
        self.t = Transform.from_rotation_translation(
            self.a, self.b, METERS, Quaternion(self.b, 0., 0., 1., 1.), (10., 20., 30.))

    def assert_code(self, code, fn, index=None):
        with self.assertRaises(SpatialError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.index, index)
        return caught.exception

    def test_analytic_sensor_aircraft_world_workflow(self):
        points = Points.from_buffer(triples([2., 3., 4.]), self.a, METERS)
        second = Transform.from_rotation_translation(
            self.b, self.c, METERS, Quaternion(self.c, 1., 1., 0., 0.), (1., -2., 3.))
        sequential = second.apply_points(self.t.apply_points(points))
        composed = self.t.then(second).apply_points(points)
        for actual, expected in zip(composed.view(), [23., 5., -31.]):
            self.assertAlmostEqual(actual, expected)
        for a, b in zip(composed.view(), sequential.view()):
            self.assertAlmostEqual(a, b)
        for actual, expected in zip(self.t.then(second).inverse().apply_points(composed).view(), points.view()):
            self.assertAlmostEqual(actual, expected)
        direction = Vectors.from_buffer(triples([2., 3., 4.]), self.a, DIMENSIONLESS)
        result = self.t.apply_vectors(direction)
        self.assertEqual(result.unit, DIMENSIONLESS)
        for actual, expected in zip(result.view(), [-3., 2., 4.]):
            self.assertAlmostEqual(actual, expected)

    def test_identity_not_name_wrapper_identity_hash(self):
        p = Points.from_buffer(triples([]), self.a, METERS)
        self.assertEqual(p.frame, self.a)
        self.assertEqual(hash(p.frame), hash(self.a))
        self.assertIsNot(p.frame, self.a)
        self.assertNotEqual(Frame("Sensor"), self.a)
        self.assertEqual({self.a: "sensor"}[p.frame], "sensor")
        self.assert_code("FrameMismatch", lambda: self.t.apply_points(
            Points.from_buffer(triples([]), Frame("Sensor"), METERS)))
        for action in [copy.copy, copy.deepcopy, pickle.dumps]:
            with self.assertRaises(TypeError):
                action(self.a)

    def test_frozen_metadata_no_subclass_or_manual_construct(self):
        p = Points.from_buffer(triples([1., 2., 3.]), self.a, METERS)
        q = Quaternion(self.b, 0., 0., 0., 1.)
        for obj, name, value in [(self.a, "name", "Other"), (p, "frame", self.b),
                                 (p, "unit", FEET), (METERS, "name", "feet"),
                                 (self.t, "source", self.c), (q, "frame", self.a)]:
            with self.assertRaises((AttributeError, TypeError)):
                setattr(obj, name, value)
        for cls in [Frame, Points, Vectors, Transform, Quaternion, Unit]:
            with self.assertRaises(TypeError):
                type("Derived", (cls,), {})
        for cls in [Points, Vectors, Transform, Unit]:
            with self.assertRaises(TypeError):
                cls()

    def test_runtime_frame_unit_kind_checks(self):
        p = Points.from_buffer(triples([1., 2., 3.]), self.a, FEET)
        self.assert_code("UnitMismatch", lambda: self.t.apply_points(p))
        self.assert_code("FrameMismatch", lambda: self.t.then(self.t))
        other = Transform.from_matrix(self.b, self.c, FEET, ID)
        self.assert_code("UnitMismatch", lambda: self.t.then(other))
        self.assert_code("FrameMismatch", lambda: Transform.from_rotation_translation(
            self.a, self.b, METERS, Quaternion(self.a, 0., 0., 0., 1.), (0., 0., 0.)))
        v = Vectors.from_buffer(triples([1., 2., 3.]), self.a, FEET)
        self.assertEqual(self.t.apply_vectors(v).unit, FEET)
        for fn in [lambda: self.t.apply_points(v), lambda: self.t.apply_vectors(p),
                   lambda: Points.from_buffer(triples([]), self.a, DIMENSIONLESS),
                   lambda: Transform.from_matrix(self.a, self.b, DIMENSIONLESS, ID),
                   lambda: Vectors.from_buffer(triples([]), self.a, DIMENSIONLESS).convert_to(METERS)]:
            with self.assertRaises(TypeError):
                fn()

    def test_buffer_shape_dtype_stride_endian_and_zero(self):
        source = triples(range(6))
        view = memoryview(source).cast("B").cast("d", shape=(2, 3))
        self.assertEqual(Points.from_buffer(view, self.a, METERS).shape, (2, 3))
        invalid = [memoryview(source)[::2], memoryview(source)[::-1],
                   memoryview(source).cast("B").cast("d", shape=(3, 2)),
                   memoryview(source).cast("B").cast("d", shape=(1, 2, 3)),
                   array.array("f", [1., 2., 3.]), bytes(24), triples([1., 2.]),
                   ctypes.c_double(1.), (ctypes.c_double * 3)(1., 2., 3.)]
        # ctypes exports '<d' here; policy accepts only native unprefixed 'd'.
        for value in invalid:
            with self.subTest(format=getattr(memoryview(value), "format", None)):
                with self.assertRaises((TypeError, ValueError, BufferError)):
                    Points.from_buffer(value, self.a, METERS)
        endian_type = ctypes.c_double.__ctype_be__ if sys.byteorder == "little" else ctypes.c_double.__ctype_le__
        endian_data = (endian_type * 3)(1., 2., 3.)
        with self.assertRaises((TypeError, ValueError, BufferError)):
            Points.from_buffer(endian_data, self.a, METERS)
        empty = Points.from_buffer(triples([]), self.a, METERS)
        self.assertEqual(empty.shape, (0, 3))
        self.assertEqual(len(empty), 0)
        self.assertEqual(empty.view().shape, (0,))
        raw = [row[:] for row in ID]; raw[0][0] = math.nan
        self.assertEqual(len(Transform.from_matrix(self.a, self.b, METERS, raw).apply_points(empty)), 0)

    def test_snapshot_alias_readonly_export_cache_lifetime(self):
        source = triples([1., 2., 3.])
        p = Points.from_buffer(memoryview(source).toreadonly(), self.a, METERS)
        source[0] = 99.
        first, second = p.view(), p.view()
        self.assertIs(first.obj, second.obj)
        self.assertIsInstance(first.obj, bytes)
        self.assertEqual(first.tolist(), [1., 2., 3.])
        self.assertTrue(first.readonly)
        with self.assertRaises(TypeError):
            first[0] = 4.
        del p, source
        gc.collect()
        self.assertEqual(first.tolist(), [1., 2., 3.])

    def test_every_import_nonfinite_and_error_index_atomicity(self):
        for bad in [math.nan, math.inf, -math.inf]:
            for axis in range(3):
                values = [1.] * 9; values[3 + axis] = bad
                for cls in [Points, Vectors]:
                    self.assert_code("NonFinite", lambda: cls.from_buffer(triples(values), self.a, METERS), 1)
        m = [row[:] for row in ID]; m[0][0] = sys.float_info.max
        transform = Transform.from_matrix(self.a, self.b, METERS, m)
        source = Points.from_buffer(triples([0., 0., 0., 2., 0., 0., 1., 0., 0.]), self.a, METERS)
        before = bytes(source.view())
        self.assert_code("NonFinite", lambda: transform.apply_points(source), 1)
        self.assertEqual(bytes(source.view()), before)
        # No output argument exists; failed output never becomes accessible.

    def test_every_raw_nonfinite_position_and_vector_ignored_entries(self):
        p = Points.from_buffer(triples([1., 2., 3.]), self.a, METERS)
        v = Vectors.from_buffer(triples([1., 2., 3.]), self.a, DIMENSIONLESS)
        for bad in [math.nan, math.inf, -math.inf]:
            for row in range(4):
                for col in range(4):
                    m = [r[:] for r in ID]; m[row][col] = bad
                    transform = Transform.from_matrix(self.a, self.b, METERS, m)
                    if row < 3:
                        self.assert_code("NonFinite", lambda: transform.apply_points(p), 0)
                    else:
                        self.assertEqual(list(transform.apply_points(p).view()), [1., 2., 3.])
                    if row < 3 and col < 3:
                        self.assert_code("NonFinite", lambda: transform.apply_vectors(v), 0)
                    else:
                        self.assertEqual(list(transform.apply_vectors(v).view()), [1., 2., 3.])

    def test_units_bits_rounding_overflow_and_transform_conversion(self):
        p = Points.from_buffer(triples([-0., math.ulp(0.), sys.float_info.min]), self.a, METERS)
        self.assertEqual(bytes(p.view()), bytes(p.convert_to(METERS).view()))
        feet = Points.from_buffer(triples([1., 2., 3.]), self.a, FEET)
        self.assertEqual(feet.convert_to(METERS).view()[0], 0.3048)
        changed = self.t.convert_to(FEET)
        for row in range(3):
            for col in range(3):
                self.assertEqual(struct.pack("d", changed.matrix[row][col]), struct.pack("d", self.t.matrix[row][col]))
        result = changed.apply_points(feet)
        self.assertEqual(result.unit, FEET)
        huge = Points.from_buffer(triples([sys.float_info.max, 0., 0.]), self.a, METERS)
        self.assert_code("NonFinite", lambda: huge.convert_to(FEET), 0)
        self.assertEqual(p.convert_to(FEET).frame, self.a)
        raw = [row[:] for row in ID]; raw[0][0] = 2.
        shear = Transform.from_matrix(self.a, self.b, METERS, raw)
        self.assertEqual(shear.apply_points(feet.convert_to(METERS)).view()[0], 0.6096)
        self.assert_code("NonRigidTransform", shear.inverse)

    def test_quaternion_extremes_and_failures(self):
        for magnitude in [sys.float_info.max, sys.float_info.min, math.ulp(0.)]:
            q = Quaternion(self.a, magnitude, -magnitude, magnitude, -magnitude)
            self.assertTrue(all(math.isfinite(x) for x in q.components))
            self.assertAlmostEqual(sum(x*x for x in q.components), 1.)
        self.assert_code("ZeroNormQuaternion", lambda: Quaternion(self.a, -0., 0., -0., 0.))
        for bad in [math.nan, math.inf, -math.inf]:
            for axis in range(4):
                values = [1.] * 4; values[axis] = bad
                self.assert_code("NonFinite", lambda: Quaternion(self.a, *values))
            self.assert_code("NonFinite", lambda: Transform.from_rotation_translation(
                self.a, self.b, METERS, Quaternion(self.b, 0., 0., 0., 1.), (bad, 0., 0.)))

    def test_concurrent_immutable_calls_and_cached_export(self):
        points = Points.from_buffer(triples([1., 2., 3.] * 10000), self.a, METERS)
        def apply(_):
            result = self.t.apply_points(points)
            return result.frame, bytes(result.view()), points.view().obj
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(apply, range(8)))
        self.assertTrue(all(x[0] == self.b and x[1] == results[0][1] for x in results))
        self.assertTrue(all(x[2] is results[0][2] for x in results))

    def test_other_objects_reject_copy_and_pickle(self):
        p = Points.from_buffer(triples([1., 2., 3.]), self.a, METERS)
        v = Vectors.from_buffer(triples([1., 2., 3.]), self.a, DIMENSIONLESS)
        q = Quaternion(self.a, 0., 0., 0., 1.)
        for obj in [p, v, self.t, q, METERS]:
            for action in [copy.copy, copy.deepcopy, pickle.dumps]:
                with self.subTest(type=type(obj).__name__, action=action.__name__):
                    with self.assertRaises(TypeError):
                        action(obj)

    @unittest.skipUnless(np is not None, "optional NumPy interop dependency not installed")
    def test_numpy_buffers_snapshot_and_readonly_view(self):
        source = np.arange(12, dtype=np.float64).reshape(4, 3)
        p = Points.from_buffer(source, self.a, METERS)
        source[:] = -99.
        view = p.view()
        output = np.asarray(view).reshape(p.shape)
        np.testing.assert_array_equal(output, np.arange(12, dtype=np.float64).reshape(4, 3))
        self.assertFalse(output.flags.writeable)
        self.assertTrue(np.shares_memory(output, np.asarray(p.view())))
        empty = Points.from_buffer(np.empty((0, 3), dtype=np.float64), self.a, METERS)
        self.assertEqual(empty.shape, (0, 3))
        for bad in [source.astype(np.float32), source[:, ::-1], np.asfortranarray(source),
                    source.astype(">f8" if sys.byteorder == "little" else "<f8"),
                    np.ndarray((1, 3), dtype=np.float64, buffer=bytearray(25), offset=1)]:
            with self.assertRaises((TypeError, ValueError, BufferError)):
                Points.from_buffer(bad, self.a, METERS)

    def test_user_guide_python_workflow(self):
        guide = Path(__file__).resolve().parents[2] / "docs" / "PYTHON-GUIDE.md"
        snippets = re.findall(r"```python\n(.*?)```", guide.read_text(encoding="utf-8"), re.S)
        self.assertTrue(snippets)
        for code in snippets:
            exec(compile(code, str(guide), "exec"), {})

    def test_packaged_typing_files(self):
        package = importlib.resources.files("spatial_typestate")
        self.assertTrue(package.joinpath("py.typed").is_file())
        self.assertTrue(package.joinpath("_native.pyi").is_file())


if __name__ == "__main__":
    unittest.main()
