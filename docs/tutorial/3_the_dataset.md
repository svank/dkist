---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# The `Dataset` Class

As previously discussed we know that a "DKIST dataset" is comprised of many files, including an ASDF and many FITS files.
The Python tools represent all these files with the {obj}`dkist.Dataset` class.

A `Dataset` class is constructed from the ASDF file for that dataset.
This ASDF file contains the following information:
* A table containing all the headers from all FITS files that comprise the dataset.
* A copy of the Data Center's inventory record for the dataset.
* A `gwcs` object which provides coordinate information for the whole dataset.
* A list of all the component FITS files and the required order to combine them into a single array.

If a `Dataset` object is created from just the ASDF file, without access to the arrays in the FITS files then all the data will be missing, but everything else will function the same.

## Constructing `Dataset` Objects

There are a two ways to construct a `Dataset`: by providing a path to an ASDF file or by providing a directory containing an ASDF file.
Here we shall first fetch an ASDF file with Fido and then pass it to `Dataset.from_asdf`:

```{code-block} python
from astropy.time import Time

import dkist
import dkist.net
from sunpy.net import Fido, attrs as a
```

```{code-block} python
# Create DKIST Fido client instance
res = Fido.search(a.dkist.Dataset('AYDEW'))

res
```
```{code-block} python
files = Fido.fetch(res, path="~/sunpy/data/{instrument}/{dataset_id}")
files
```

Remember that the file we have downloaded is a single ASDF file, **not** the whole dataset.
We can use this file to construct the `Dataset`:

```{code-block} python
ds = dkist.Dataset.from_asdf(files[0])
```

Now we have a `Dataset` object which describes the shape, size and physical dimensions of the array, but doesn't yet contain any of the actual data.
This may sound unhelpful but we'll see how it can be very powerful.

First let's have a look at the basic representation of the `Dataset`.

```{code-block} python
ds
```

This tells us that we have a 4-dimensional data cube and what values the axes correspond to.
Importantly, it not only gives us information about the *pixel* axes (the actual dimensions of the array itself), but also the *world* axes (the physical quantities related to the observation).
It also gives us a correlation matrix showing how the pixel axes relate to the world axes.

## `Dataset` and `NDCube`: Coordinate aware arrays

The `Dataset` class is an extension to [SunPy's `NDCube` class](https://docs.sunpy.org/projects/ndcube/), in this section we shall demonstrate some of the key functionality of `NDCube` with DKIST data.

### Pixel, Array and World Ordering

Before we jump into using the `Dataset` class we need to clarify some definitions:

* **Pixel** ordering is defined as "Cartesian" ordering, or the same as Fortran ordering or column major. This is the ordering used by FITS files and WCS objects in Python.
* **Array** ordering is defined as C or row-major ordering. This is used by Python's numpy arrays, as Python is implemented in C.
* **World** coordinates are the physical coordinates that correspond to pixel coordinates. These are not always in either pixel or array order, but tend to be close to pixel order.


### Coordinates, Arrays, Pixels, oh my!

A key aspect of the `Dataset` is that it is coordinate aware.
That is, it is able to map between array indices and physical dimensions.
This means that you can easily convert from a position in the array to a location defined by physical coordinates.

The first thing we can inspect about our dataset is the dimensionality of the underlying array.
```{code-block} python
ds.dimensions
```

These are the **array** dimensions.
We can get the corresponding **pixel** axis names with:

```{code-block} python
ds.wcs.pixel_axis_names
```

note how these are reversed from one another, we can print them together with:
```{code-block} python
for name, length in zip(ds.wcs.pixel_axis_names[::-1], ds.dimensions):
    print(f"{name}: {length}")
```

These axes map onto world axes via the axis correlation matrix we saw in the first section:
```{code-block} python
ds.wcs.axis_correlation_matrix
```

We can get a list of the world axes which correspond to each array axis with:
```{code-block} python
ds.array_axis_physical_types
```

Finally, as we saw in the first session, we can convert between pixel or array coordinates and world coordinates:

```{code-block} python
# Convert array indices to world (physical) coordinates
ds.wcs.array_index_to_world(0, 10, 20, 30)
```

```{code-block} python
# Convert pixel coords to world coords
world = ds.wcs.pixel_to_world(30, 20, 10, 0)
world
```

and we can also do the reverse:

```{code-block} python
ds.wcs.world_to_pixel(*world)
```

```{code-block} python
ds.wcs.world_to_array_index(*world)
```

Finally, it's possible to get all the axis coordinates along one or more axes:

```{warning}
This might eat all your <del>cat</del> RAM.

The algorithm used to calculate these coordinates in ndcube isn't as memory efficient as it could be, and when working with the large multi-dimensional DKIST data you can really notice it!

This will be improved in later versions of the `dkist` package.
```

```{code-block} python
ds.axis_world_coords()
```

```{code-block} python
ds.axis_world_coords('time')
```

### Slicing Datasets

Another useful feature of the `Dataset` class, which it inherits from `NDCube` is the ability to "slice" the dataset and get a smaller dataset, with the array and coordinate information in tact.

For example, to extract the Stokes I component of the dataset we would do:

```{code-block} python
ds[0]
```

This is because the Stokes axis is the first array axis, and the "I" profile is the first one (0-indexing).

Note how we have dropped a world coordinate; this information is preserved in the `.global_coords` attribute, which contains the coordinate information which applies to the whole dataset:

```{code-block} python
ds[0].global_coords
```

We can also slice out a section of an axis of the dataset:

```{code-block} python
ds[:, 100:200, :, :]
```

This selects only 100 of the raster step points.


## TiledDataset

So far we have been working with VISP data, which is continuous in a sense, in that there are no gaps or overlaps in the coordinates axes.
However, instruments like VBI take multiple images at different locations with the intention of tiling them together to form a larger image.
In this case, those images do not share a common pixel grid and therefore cannot be simply stacked together.
It is possible to use `reproject` to regrid the images into a larger array, but since this would interpolate the data, it is not done by default.
We will cover an example of how to do this later in the workshop.

This kind of tiled data cannot be stored in a single `Dataset` object.
There is therefore a wrapper object called `TiledDataset`, which is essentially an array of `Dataset` objects.
Let's demonstrate this with a VBI dataset.

```{code-block} python
res = Fido.search(a.dkist.Dataset('BLKGA'))
files = Fido.fetch(res, path="~/sunpy/data/{instrument}/{dataset_id}")
tds = dkist.Dataset.from_asdf(files[0])
tds
```

To access the individual tiles, we can then index this normally to get back the `Dataset` objects.

```{code-block} python
ds = tds[0, 0]
ds
```

```{error}
Due to a known issue with the VBI level 1 FITS headers, the ordering of these tiles in the array is likley incorrect.
```

The `TiledDataset` stores the FITS headers for all the files of the individual `Dataset`s in the `combined_headers` attribute.
This means that the metadata can still be inspected in many of the ways we will see in later sessions.
Later releases of the user tools will also include helper functions for regridding a `TiledDataset` into a single `Dataset` object.