"""
This file contains code to lazy-load arrays from FITS files. It is designed to
minimise (virtual) memory usage and the number of open files.
"""

import os
import abc

from astropy.io import fits
from sunpy.util.decorators import add_common_docstring

__all__ = ['BaseFITSLoader', 'AstropyFITSLoader']

common_parameters = """

    Parameters
    ----------

    externalarray: `asdf.ExternalArrayReference`
        The asdf array reference, must be to a FITS file (although this is not validated).

    basepath: `str`
        The base path for the filenames in the `asdf.ExternalArrayReference`,
        if not specified the filepaths are treated as absolute.
"""


@add_common_docstring(append=common_parameters)
class BaseFITSLoader(metaclass=abc.ABCMeta):
    """
    Base class for resolving an `asdf.ExternalArrayReference` to a FITS file.
    """

    def __init__(self, externalarray, basepath=None):
        self.fitsarray = externalarray
        self.basepath = basepath
        # Private cache
        self._array = None
        self._fits_header = None
        # These are needed for this object to be array-like
        self.shape = self.fitsarray.shape
        self.dtype = self.fitsarray.dtype

    def __repr__(self):
        # repr alone should not force loading of the data
        if self._array is None:
            return "<FITS array (unloaded) in {0} shape: {1} dtype: {2}>".format(
                self.fitsarray.fileuri, self.fitsarray.shape, self.fitsarray.dtype)
        return repr(self._array)

    def __str__(self):
        # str alone should not force loading of the data
        if self._array is None:
            return "<FITS array (unloaded) in {0} shape: {1} dtype: {2}>".format(
                self.fitsarray.fileuri, self.fitsarray.shape, self.fitsarray.dtype)
        return str(self._array)

    def __array__(self):
        return self.fits_array

    def __getitem__(self, slc):
        return self.fits_array[slc]

    @property
    def absolute_uri(self):
        """
        Construct a non-relative path to the file, using ``basepath`` if provided.
        """
        if self.basepath:
            return os.path.join(self.basepath, self.fitsarray.fileuri)
        else:
            return self.fitsarray.fileuri

    @property
    def fits_header(self):
        """
        The FITS header for this file.

        .. note::

            This will be read from the file on access if it is not already cached.

        """
        if not self._fits_header:
            self._fits_header = self._read_fits_header()
        return self._fits_header

    @property
    def fits_array(self):
        """
        The FITS array object.
        """
        if self._array is None:
            self._array = self._read_fits_array()
        return self._array

    @abc.abstractmethod
    def _read_fits_header(self):
        """
        Read and return the FITS header.

        .. note::

            This method must not leave the file open.

        """

    @abc.abstractmethod
    def _read_fits_array(self):
        """
        Read and return a reference to the FITS array.

        .. note::

            If it works with the underlying library, reading the header into
            the cache while the file is open is worthwhile.
        """


@add_common_docstring(append=common_parameters)
class AstropyFITSLoader(BaseFITSLoader):
    """
    Resolve an `~asdf.ExternalArrayReference` to a FITS file using `astropy.io.fits`.
    """

    def _read_fits_array(self):
        """
        Make sure we cache the header while we have the file open.
        """
        with fits.open(self.absolute_uri, memmap=True, do_not_scale_image_data=False, mode="denywrite") as hdul:
            hdul.verify('fix')
            hdu = hdul[self.fitsarray.target]
            if not self._fits_header:
                self._fits_header = hdu.header
            return hdu.data

    def _read_fits_header(self):
        """
        Just read the header, used if the header is requested before the data.
        """
        with fits.open(self.absolute_uri) as hdul:
            hdul.verify('fix')
            hdu = hdul[self.fitsarray.target]
            return hdu.header
