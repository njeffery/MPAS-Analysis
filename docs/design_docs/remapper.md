Remapper for "online" remapping of data sets
============================================

<h2>
Xylar Asay-Davis <br>
date: 2017/04/15 <br>
</h2>
<h3> Summary </h3>

This document describes the design and implementation of a `Remapper` class
for performing either "online" (in memory) or "offline" (through files
via `ncremap`) remapping of horizontal data sets.  The `Remapper` is needed in
order to support remapping to and from grids grids not currently supported by
`ncremap` such as polar stereographic grids commonly used for polar data sets.


<h3> Requirements </h3>

<h3> Requirement: Support for remapping to and from stereographic grids <br>
Date last modified: 2017/04/15 <br>
Contributors: Xylar Asay-Davis
</h3>

There should exist a method for interpolating from stereographic grids to
the comparison grid used in MPAS-Analysis.  This is needed to support
observations that are stored on stereographic grids.

It would often be more efficient (in terms of the size of data sets) and more
practical to perform analysis of polar data sets on a stereographic grid
centered at that pole.  Support for mapping to stereographic grids should be
included, if feasible.


<h3> Algorithmic Formulations</h3>

<h3> Design solution: Support for remapping to and from stereographic grids <br>
Date last modified: 2017/04/15 <br>
Contributors: Xylar Asay-Davis
</h3>

The design solution is somewhat complex and will be described in multiple
sections.

<h4> MeshDescriptor classes </h4>

To support mapping to and from MPAS meshes, lat/lon grid and stereographic
grids (as well as future grids we might want to support), I propose defining a
"mesh descriptor" that defines the mesh either by reading it from a file or by
creating it from simple numpy ndarrays.  Each `MeshDescriptor` class defines
enough information (such as the locations of cell centers and corners) about
the mesh or grid to allow remapping between meshes.

An `MpasMeshDescriptor` class will define MPAS meshes read from a file.

A `LatLonGridDescriptor` class will define global lat/lon grids such as the
existing comparison grid.

A `ProjectionGridDescriptor` class will define any grid that can be described
by a logically rectangular grid with `pyproj` projection.  In particular, such
a projection grid could be used to support both polar stereographic grids and
regional lat/lon grids.

<h4> Remapper class </h4>

Remapping between meshes described by `MeshDescriptor` classes will be performed
by a `Remapper` class.  This class will support both "online" mapping in memory
and "offline" mapping with `ncremap`.  Only "online" mapping will be supported
for grids defined with the `ProjectionGridDescriptor`, as these are not
supported by `ncremap`.  A `Remapper` object will be created by giving it source
and destintion `MeshDescriptor` objects and an optional mapping file name.
(If the mapping file name is not given, it is assumed that the source and
destination grids are the same, and no remapping is needed.)

If remapping is performed "online", it supports renormalization of masked
arrays.  If a data sets includes `NaN`s in a given data array, both the data
array and a mask are remapped, and renormalization is performed anywhere the
remapped mask exceeds a given threshold.


<h3> Design and Implementation </h3>

<h3> Implementation: Support for remapping to and from stereographic grids <br>
Date last modified: 2017/04/15 <br>
Contributors: Xylar Asay-Davis
</h3>

The implementation is on the branch [xylar/MPAS-Analysis/add_polar_stereographic_interp](https://github.com/xylar/MPAS-Analysis/tree/add_polar_stereographic_interp)

<h4> MeshDescriptor classes </h4>

Each `MeshDescriptor` subclass includes the following member variables or
methods:
  * `meshName`: a name of the mesh or grid, used for naming mapping files and
     climatologies
  * `regional`: whether the mesh is regional or global
  * `coords` and `dims`: dictionaries defining the coordinates and dimensions
     of this mesh, used to update a data set following remapping
  * `to_scrip` method: used to write out a SCRIP file defining the mesh.

<h4> Remapper class </h4>

Below is a skeleton of the `Remapper` public API.

```python
class Remapper(object):
    def __init__(self, sourceDescriptor, destinationDescriptor,
                 mappingFileName=None):
        '''
        Create the remapper and read weights and indices from the given file
        for later used in remapping fields.
        '''

    def build_mapping_file(self, method='bilinear',
                           additionalArgs=None):
        '''
        Given a source file defining either an MPAS mesh or a lat-lon grid and
        a destination file or set of arrays defining a lat-lon grid, constructs
        a mapping file used for interpolation between the source and
        destination grids.
        '''

    def remap_file(self, inFileName, outFileName,
                   variableList=None, overwrite=False):
        '''
        Given a source file defining either an MPAS mesh or a lat-lon grid and
        a destination file or set of arrays defining a lat-lon grid, constructs
        a mapping file used for interpolation between the source and
        destination grids.
        '''

    def remap(self, ds, renormalizationThreshold=None):
        '''
        Given a source data set, returns a remapped version of the data set,
        possibly masked and renormalized.
        '''
```

<h3> Testing and Validation: Support for remapping to and from stereographic
grids <br>
Date last modified: 2017/04/15 <br>
Contributors: Xylar Asay-Davis
</h3>

On the branch [xylar/MPAS-Analysis/add_polar_stereographic_interp](https://github.com/xylar/MPAS-Analysis/tree/add_polar_stereographic_interp),
climatologies have ben updated to use `Remapper` objects.  Analysis has been
run on both `QU240` and `EC60to30` beta0 ACME results, and results have been
compared by eye.  Results from `ncremap` are identical, as expected.  Because of
renormalization, results with "online" remapping differ from those from
`ncremap`, typically with less severe masking of missing data.

Continuous integration unit tests for climatology and interpolation have both
been updated to make use of the `Remapper` class.  New tests have been added to
perform remapping with stereographic grids.

