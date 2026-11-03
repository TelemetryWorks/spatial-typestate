//! Batch-only CPython adapter; all spatial arithmetic delegates to the core.
#![deny(unsafe_code)]

mod kernels;

use std::hash::{Hash, Hasher};
use std::sync::Arc;

use pyo3::buffer::PyUntypedBuffer;
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyBytes, PyType};
use spatial_typestate::{Frame as CoreFrame, SpatialError as CoreError, UnitQuat};

pyo3::create_exception!(_native, SpatialError, PyValueError);

struct Source;
struct Target;
struct Next;
impl CoreFrame for Source {}
impl CoreFrame for Target {}
impl CoreFrame for Next {}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Kind {
    Meters,
    Feet,
    Dimensionless,
}

#[pyclass(frozen, from_py_object, module = "spatial_typestate._native")]
#[derive(Clone)]
struct Unit {
    kind: Kind,
}

#[pymethods]
impl Unit {
    #[getter]
    fn name(&self) -> &'static str {
        match self.kind {
            Kind::Meters => "meters",
            Kind::Feet => "feet",
            Kind::Dimensionless => "dimensionless",
        }
    }
    fn __repr__(&self) -> String {
        format!("Unit({})", self.name())
    }
    fn __eq__(&self, other: &Self) -> bool {
        self.kind == other.kind
    }
    fn __hash__(&self) -> usize {
        self.kind as usize
    }
}

#[pyclass(frozen, from_py_object, module = "spatial_typestate._native")]
#[derive(Clone)]
struct Frame {
    id: Arc<String>,
}

#[pymethods]
impl Frame {
    #[new]
    fn new(name: String) -> PyResult<Self> {
        if name.is_empty() {
            return Err(PyValueError::new_err("frame name must not be empty"));
        }
        Ok(Self { id: Arc::new(name) })
    }
    #[getter]
    fn name(&self) -> &str {
        &self.id
    }
    fn __repr__(&self) -> String {
        format!("Frame({:?})", self.name())
    }
    fn __eq__(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.id, &other.id)
    }
    fn __hash__(&self) -> u64 {
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        Arc::as_ptr(&self.id).hash(&mut hasher);
        hasher.finish()
    }
    fn __copy__(&self) -> PyResult<()> {
        Err(PyTypeError::new_err("frame identity cannot be copied"))
    }
    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> PyResult<()> {
        self.__copy__()
    }
    fn __reduce_ex__(&self, _protocol: i32) -> PyResult<()> {
        Err(PyTypeError::new_err("frame identity cannot be pickled"))
    }
}

fn error(
    py: Python<'_>,
    code: &str,
    index: Option<usize>,
    message: impl std::fmt::Display,
) -> PyErr {
    let err = SpatialError::new_err(message.to_string());
    let value = err.value(py);
    // These are ordinary exception attributes, never consulted for validation.
    if let Err(e) = value.setattr("code", code) {
        return e;
    }
    if let Err(e) = value.setattr("index", index) {
        return e;
    }
    err
}

fn core_error(py: Python<'_>, e: CoreError, index: Option<usize>) -> PyErr {
    let code = match e {
        CoreError::NonFinite => "NonFinite",
        CoreError::ZeroNormQuaternion => "ZeroNormQuaternion",
        CoreError::NonRigidTransform => "NonRigidTransform",
        CoreError::InvalidUnitScale => "InvalidUnitScale",
        CoreError::UnrepresentableUnitConversion => "UnrepresentableUnitConversion",
    };
    error(py, code, index, e)
}
fn same_frame(py: Python<'_>, a: &Frame, b: &Frame) -> PyResult<()> {
    if a.__eq__(b) {
        Ok(())
    } else {
        Err(error(py, "FrameMismatch", None, "frame identities differ"))
    }
}
fn length(unit: &Unit) -> PyResult<()> {
    if unit.kind == Kind::Dimensionless {
        Err(PyTypeError::new_err("a length unit is required"))
    } else {
        Ok(())
    }
}
fn same_unit(py: Python<'_>, a: Kind, b: Kind) -> PyResult<()> {
    if a == b {
        Ok(())
    } else {
        Err(error(
            py,
            "UnitMismatch",
            None,
            "explicit unit conversion required",
        ))
    }
}

struct Data {
    values: Vec<f64>,
    frame: Frame,
    unit: Unit,
    bytes: PyOnceLock<Py<PyBytes>>,
}

fn byte_len(count: usize) -> PyResult<usize> {
    count
        .checked_mul(8)
        .filter(|n| *n <= isize::MAX as usize)
        .ok_or_else(|| PyValueError::new_err("batch exceeds addressable buffer size"))
}
impl Data {
    fn owned(values: Vec<f64>, frame: Frame, unit: Unit) -> Self {
        Self {
            values,
            frame,
            unit,
            bytes: PyOnceLock::new(),
        }
    }
    fn import(
        py: Python<'_>,
        value: &Bound<'_, PyAny>,
        frame: Frame,
        unit: Unit,
    ) -> PyResult<Self> {
        let buffer = PyUntypedBuffer::get(value)?;
        let shape = buffer.shape();
        if buffer.format().to_bytes() != b"d" || buffer.item_size() != 8 {
            return Err(PyTypeError::new_err("expected native float64 format 'd'"));
        }
        if !buffer.is_c_contiguous() || buffer.suboffsets().is_some() {
            return Err(PyValueError::new_err(
                "expected a direct C-contiguous buffer",
            ));
        }
        if !((shape.len() == 1 && shape[0] % 3 == 0) || (shape.len() == 2 && shape[1] == 3)) {
            return Err(PyValueError::new_err("expected shape (N,3) or flat 3*N"));
        }
        byte_len(buffer.item_count())?;
        // Some valid zero-sized exporters use a non-aligned null/sentinel pointer.
        // No element is read for an empty buffer, so typed alignment is irrelevant.
        let values = if buffer.item_count() == 0 {
            Vec::new()
        } else {
            buffer.as_typed::<f64>()?.to_vec(py)?
        };
        drop(buffer); // foreign storage is never accessed by detached work
        if let Some(i) = values.iter().position(|v| !v.is_finite()) {
            return Err(core_error(py, CoreError::NonFinite, Some(i / 3)));
        }
        Ok(Self::owned(values, frame, unit))
    }
    fn view<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let bytes = self.bytes.get_or_try_init(py, || {
            PyBytes::new_with(py, byte_len(self.values.len())?, |out| {
                for (chunk, value) in out.chunks_exact_mut(8).zip(&self.values) {
                    chunk.copy_from_slice(&value.to_ne_bytes());
                }
                Ok(())
            })
            .map(Bound::unbind)
        })?;
        py.import("builtins")?
            .getattr("memoryview")?
            .call1((bytes.bind(py),))?
            .call_method1("cast", ("d",))
    }
    fn convert(&self, py: Python<'_>, unit: Unit) -> PyResult<Self> {
        length(&self.unit)?;
        length(&unit)?;
        let values = py
            .detach(|| kernels::convert(&self.values, self.unit.kind, unit.kind))
            .map_err(|(i, e)| core_error(py, e, Some(i)))?;
        Ok(Self::owned(values, self.frame.clone(), unit))
    }
}

#[pyclass(frozen, module = "spatial_typestate._native")]
struct Points {
    data: Data,
}
#[pymethods]
impl Points {
    #[classmethod]
    fn from_buffer(
        _cls: &Bound<'_, PyType>,
        py: Python<'_>,
        buffer: &Bound<'_, PyAny>,
        frame: Frame,
        unit: Unit,
    ) -> PyResult<Self> {
        length(&unit)?;
        Ok(Self {
            data: Data::import(py, buffer, frame, unit)?,
        })
    }
    #[getter]
    fn frame(&self) -> Frame {
        self.data.frame.clone()
    }
    #[getter]
    fn unit(&self) -> Unit {
        self.data.unit.clone()
    }
    #[getter]
    fn shape(&self) -> (usize, usize) {
        (self.data.values.len() / 3, 3)
    }
    fn __len__(&self) -> usize {
        self.shape().0
    }
    fn view<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        self.data.view(py)
    }
    fn convert_to(&self, py: Python<'_>, unit: Unit) -> PyResult<Self> {
        Ok(Self {
            data: self.data.convert(py, unit)?,
        })
    }
}
#[pyclass(frozen, module = "spatial_typestate._native")]
struct Vectors {
    data: Data,
}
#[pymethods]
impl Vectors {
    #[classmethod]
    fn from_buffer(
        _cls: &Bound<'_, PyType>,
        py: Python<'_>,
        buffer: &Bound<'_, PyAny>,
        frame: Frame,
        unit: Unit,
    ) -> PyResult<Self> {
        Ok(Self {
            data: Data::import(py, buffer, frame, unit)?,
        })
    }
    #[getter]
    fn frame(&self) -> Frame {
        self.data.frame.clone()
    }
    #[getter]
    fn unit(&self) -> Unit {
        self.data.unit.clone()
    }
    #[getter]
    fn shape(&self) -> (usize, usize) {
        (self.data.values.len() / 3, 3)
    }
    fn __len__(&self) -> usize {
        self.shape().0
    }
    fn view<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        self.data.view(py)
    }
    fn convert_to(&self, py: Python<'_>, unit: Unit) -> PyResult<Self> {
        Ok(Self {
            data: self.data.convert(py, unit)?,
        })
    }
}

#[pyclass(frozen, module = "spatial_typestate._native")]
struct Quaternion {
    frame: Frame,
    value: UnitQuat<Target>,
}
#[pymethods]
impl Quaternion {
    #[new]
    fn new(py: Python<'_>, frame: Frame, x: f64, y: f64, z: f64, w: f64) -> PyResult<Self> {
        Ok(Self {
            frame,
            value: UnitQuat::try_from_components(x, y, z, w)
                .map_err(|e| core_error(py, e, None))?,
        })
    }
    #[getter]
    fn frame(&self) -> Frame {
        self.frame.clone()
    }
    #[getter]
    fn components(&self) -> (f64, f64, f64, f64) {
        (
            self.value.x(),
            self.value.y(),
            self.value.z(),
            self.value.w(),
        )
    }
}

#[pyclass(frozen, module = "spatial_typestate._native")]
struct Transform {
    source: Frame,
    target: Frame,
    unit: Unit,
    matrix: [[f64; 4]; 4],
}
#[pymethods]
impl Transform {
    #[classmethod]
    fn from_rotation_translation(
        _cls: &Bound<'_, PyType>,
        py: Python<'_>,
        source: Frame,
        target: Frame,
        unit: Unit,
        rotation: &Quaternion,
        translation: [f64; 3],
    ) -> PyResult<Self> {
        length(&unit)?;
        same_frame(py, &target, &rotation.frame)?;
        let matrix = kernels::construct(unit.kind, rotation.value, translation)
            .map_err(|e| core_error(py, e, None))?;
        Ok(Self {
            source,
            target,
            unit,
            matrix,
        })
    }
    #[classmethod]
    fn from_matrix(
        _cls: &Bound<'_, PyType>,
        source: Frame,
        target: Frame,
        unit: Unit,
        matrix: [[f64; 4]; 4],
    ) -> PyResult<Self> {
        length(&unit)?;
        Ok(Self {
            source,
            target,
            unit,
            matrix,
        })
    }
    #[getter]
    fn source(&self) -> Frame {
        self.source.clone()
    }
    #[getter]
    fn target(&self) -> Frame {
        self.target.clone()
    }
    #[getter]
    fn unit(&self) -> Unit {
        self.unit.clone()
    }
    #[getter]
    fn matrix(&self) -> [[f64; 4]; 4] {
        self.matrix
    }
    fn apply_points(&self, py: Python<'_>, points: &Points) -> PyResult<Points> {
        same_frame(py, &self.source, &points.data.frame)?;
        same_unit(py, self.unit.kind, points.data.unit.kind)?;
        let values = py
            .detach(|| kernels::points(self.matrix, self.unit.kind, &points.data.values))
            .map_err(|(i, e)| core_error(py, e, Some(i)))?;
        Ok(Points {
            data: Data::owned(values, self.target.clone(), self.unit.clone()),
        })
    }
    fn apply_vectors(&self, py: Python<'_>, vectors: &Vectors) -> PyResult<Vectors> {
        same_frame(py, &self.source, &vectors.data.frame)?;
        let values = py
            .detach(|| kernels::vectors(self.matrix, vectors.data.unit.kind, &vectors.data.values))
            .map_err(|(i, e)| core_error(py, e, Some(i)))?;
        Ok(Vectors {
            data: Data::owned(values, self.target.clone(), vectors.data.unit.clone()),
        })
    }
    fn then(&self, py: Python<'_>, next: &Transform) -> PyResult<Self> {
        same_frame(py, &self.target, &next.source)?;
        same_unit(py, self.unit.kind, next.unit.kind)?;
        let matrix = kernels::compose(self.matrix, next.matrix, self.unit.kind)
            .map_err(|e| core_error(py, e, None))?;
        Ok(Self {
            source: self.source.clone(),
            target: next.target.clone(),
            unit: self.unit.clone(),
            matrix,
        })
    }
    fn inverse(&self, py: Python<'_>) -> PyResult<Self> {
        let matrix =
            kernels::inverse(self.matrix, self.unit.kind).map_err(|e| core_error(py, e, None))?;
        Ok(Self {
            source: self.target.clone(),
            target: self.source.clone(),
            unit: self.unit.clone(),
            matrix,
        })
    }
    fn convert_to(&self, py: Python<'_>, unit: Unit) -> PyResult<Self> {
        length(&unit)?;
        let matrix = kernels::convert_transform(self.matrix, self.unit.kind, unit.kind)
            .map_err(|e| core_error(py, e, None))?;
        Ok(Self {
            source: self.source.clone(),
            target: self.target.clone(),
            unit,
            matrix,
        })
    }
}

#[pymodule(gil_used = true)]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Frame>()?;
    m.add_class::<Unit>()?;
    m.add_class::<Points>()?;
    m.add_class::<Vectors>()?;
    m.add_class::<Quaternion>()?;
    m.add_class::<Transform>()?;
    m.add("SpatialError", m.py().get_type::<SpatialError>())?;
    m.add("METERS", Unit { kind: Kind::Meters })?;
    m.add("FEET", Unit { kind: Kind::Feet })?;
    m.add(
        "DIMENSIONLESS",
        Unit {
            kind: Kind::Dimensionless,
        },
    )?;
    Ok(())
}

#[cfg(test)]
mod boundary_tests {
    use super::*;
    #[test]
    fn capacity_guards_do_not_allocate() {
        assert_eq!(byte_len(0).unwrap(), 0);
        assert_eq!(
            byte_len((isize::MAX as usize) / 8).unwrap(),
            ((isize::MAX as usize) / 8) * 8
        );
        assert!(byte_len((isize::MAX as usize) / 8 + 1).is_err());
        assert!(byte_len(usize::MAX).is_err());
    }
}
