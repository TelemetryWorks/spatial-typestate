# Coordinate interpretation

The checked quaternion transform constructor uses right-handed Hamilton algebra,
components (x,y,z,w), and column vectors: p_To = R(q)*p_From + t_To.
The columns of R are the From basis vectors expressed in To. Translation is
the From origin expressed in To. A positive quarter turn about z sends numeric
+x to +y; a positive quarter turn about x sends +y to +z.

These rules define the constructor's numeric rotation convention, not a global
choice of aircraft forward/down axes, world origin, or active/passive
physical interpretation. The application must choose consistent physical frames
and supply their relationship. Raw matrices may represent other linear maps;
application/composition check participating finiteness, while checked inverse
also validates rigidity. Points/translation use an explicit common length tag;
vectors preserve a separate unit tag. Tags cannot validate measurements, custom
unit declarations or dimensional correctness of raw coefficients. See [units](units.md).

In the [sensor example](../examples/sensor_alignment.rs), sensor->aircraft uses
Rz(+90) and target offset (1,2,3); aircraft->world uses Rx(+90) and target offset
(10,20,30). Point (2,0,1) becomes (1,4,4), then (11,16,34). The corresponding
vector becomes (0,-1,2), with no translation. These are analytic numeric choices,
not a physical sensor calibration or a prescribed aerospace axis convention.

See [matrix algebra and numerical limits](math_conventions.md).
