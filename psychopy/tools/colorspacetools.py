#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2015 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

"""Functions and classes related to color space conversion
"""
from __future__ import absolute_import, division, print_function

from past.utils import old_div
import numpy

from psychopy import logging
from psychopy.tools.coordinatetools import sph2cart


def unpackColors(colors):
    """Reshape an array of color values to Nx3 format.

    Many color conversion routines operate on color data in Nx3 format, where
    rows are color space coordinates. 1x3 and NxNx3 input are converted to Nx3
    format.

    :param colors:
        Nx3 or NxNx3 array of colors, last dim must be size == 3 specifying each
        color coordinate.
    :return: Nx3 ndarray of converted colors, original shape, original dims

    """
    # handle the various data types and shapes we might get as input
    if isinstance(colors, (list, tuple,)):
        colors = numpy.asarray(colors)

    orig_shape = colors.shape
    orig_dim = colors.ndim
    if orig_dim == 1 and orig_shape[0] == 3:
        colors = numpy.array(colors, ndmin=2)
    elif orig_dim == 2 and orig_shape[1] == 3:
        pass
    elif orig_dim == 3 and orig_shape[2] == 3:
        colors = numpy.reshape(colors, (-1, 3))
    else:
        raise ValueError(
            "Invalid input dimensions or shape for input colors.")

    return colors, orig_shape, orig_dim


def srgbTF(rgb, reverse=False, **kwargs):
    """Apply sRGB transfer function (or gamma) to RGB values.

    Input values must have been transformed using a conversion matrix derived
    from sRGB primaries relative to D65.

    :param rgb: tuple, list or ndarray of floats
        Nx3 or NxNx3 array of linear RGB values, last dim must be size == 3
        specifying RBG values.
    :param reverse: boolean
        If True, the reverse transfer function will convert sRGB -> linear RGB
    :return: ndarray with same shape as input

    """
    rgb, orig_shape, orig_dim = unpackColors(rgb)

    # apply the sRGB TF
    if not reverse:
        # applies the sRGB transfer function (linear RGB -> sRGB)
        to_return = numpy.where(
            rgb <= 0.0031308,
            rgb * 12.92,
            (1.0 + 0.055) * rgb ** (1.0 / 2.4) - 0.055)
    else:
        # do the inverse (sRGB -> linear RGB)
        to_return = numpy.where(
            rgb <= 0.04045,
            rgb / 12.92,
            ((rgb + 0.055) / 1.055) ** 2.4)

    if orig_dim == 1:
        to_return = to_return[0]
    elif orig_dim == 3:
        to_return = numpy.reshape(to_return, orig_shape)

    return to_return


def rec709TF(rgb, **kwargs):
    """Apply the Rec. 709 transfer function (or gamma) to linear RGB values.

    This transfer function is defined in the ITU-R BT.709 (2015) recommendation
    document (http://www.itu.int/rec/R-REC-BT.709-6-201506-I/en) and is
    commonly used with HDTV televisions.

    :param rgb: tuple, list or ndarray of floats
        Nx3 or NxNx3 array of linear RGB values, last dim must be size == 3
        specifying RBG values.
    :return: ndarray with same shape as input

    """
    rgb, orig_shape, orig_dim = unpackColors(rgb)

    # applies the Rec.709 transfer function (linear RGB -> Rec.709 RGB)
    # mdc - I didn't compute the inverse for this one.
    to_return = numpy.where(rgb >= 0.018,
                            1.099 * rgb ** 0.45 - 0.099,
                            4.5 * rgb)

    if orig_dim == 1:
        to_return = to_return[0]
    elif orig_dim == 3:
        to_return = numpy.reshape(to_return, orig_shape)

    return to_return


def cielab2rgb(lab,
               whiteXYZ=None,
               conversionMatrix=None,
               transferFunc=None,
               clip=False,
               **kwargs):
    """Transform CIEL*a*b* (1976) color space coordinates to RGB tristimulus
    values.

    CIEL*a*b* are first transformed into CIE XYZ (1931) color space, then the
    RGB conversion is applied. By default, the sRGB conversion matrix is used
    with a reference D65 white point. You may specify your own RGB conversion
    matrix and white point (in CIE XYZ) appropriate for your display.

    Parameters
    ----------

    :param lab: tuple, list or ndarray
        1-, 2-, 3-D vector of CIEL*a*b* coordinates to convert. The last
        dimension should be length-3 in all cases specifying a single
        coordinate.
    :param whiteXYZ: tuple, list or ndarray
        1-D vector coordinate of the white point in CIE-XYZ color space. Must be
        the same white point needed by the conversion matrix. The default
        white point is D65 if None is specified, defined as:
            X, Y, Z = 0.9505, 1.0000, 1.0890
    :param conversionMatrix: tuple, list or ndarray
        3x3 conversion matrix to transform CIE-XYZ to linear RGB values. The
        default matrix is sRGB with a D65 white point if None is specified.
    :param transferFunc: pyfunc or None
        Signature of the transfer function to use. If None, values are kept as
        linear RGB (it's assumed your display is gamma corrected via the
        hardware CLUT). The TF must be appropriate for the conversion matrix
        supplied (default is sRGB). Additional arguments to 'transferFunc' can
        be passed by specifying them as keyword arguments. Gamma functions that
        come with PsychoPy are 'srgbTF' and 'rec709TF', see their docs for more
        information.
    :param clip: boolean
        Make all output values representable by the display. However, colors
        outside of the display's gamut may not be valid!
    :return: array of RGB tristimulus values, or None

    Example
    -------

    import psychopy.tools.colorspacetools as cst
    cielabColor = (53.0, -20.0, 0.0)  # greenish color (L*, a*, b*)
    # convert a CIEL*a*b* color to signed RGB with sRGB transfer function
    rgbColor = cst.cielab2rgb(cielabColor, transferFunc=cst.srgbTF)

    """
    lab, orig_shape, orig_dim = unpackColors(lab)

    if conversionMatrix is None:
        # XYZ -> sRGB conversion matrix, assumes D65 white point
        # mdc - computed using makeXYZ2RGB with sRGB primaries
        conversionMatrix = numpy.asmatrix([
            [3.24096994, -1.53738318, -0.49861076],
            [-0.96924364, 1.8759675, 0.04155506],
            [0.05563008, -0.20397696, 1.05697151]
        ])

    if whiteXYZ is None:
        # D65 white point in CIE-XYZ color space
        #   See: https://en.wikipedia.org/wiki/SRGB
        whiteXYZ = numpy.asarray([0.9505, 1.0000, 1.0890])

    L = lab[:, 0]  # lightness
    a = lab[:, 1]  # green (-)  <-> red (+)
    b = lab[:, 2]  # blue (-) <-> yellow (+)
    wht_x, wht_y, wht_z = whiteXYZ  # white point in CIE-XYZ color space

    # convert Lab to CIE-XYZ color space
    # uses reverse transformation found here:
    #   https://en.wikipedia.org/wiki/Lab_color_space
    xyz_array = numpy.zeros(lab.shape)
    s = (L + 16.0) / 116.0
    xyz_array[:, 0] = s + (a / 500.0)
    xyz_array[:, 1] = s
    xyz_array[:, 2] = s - (b / 200.0)

    # evaluate the inverse f-function
    delta = 6.0 / 29.0
    xyz_array = numpy.where(xyz_array > delta,
                            xyz_array ** 3.0,
                            (xyz_array - (4.0 / 29.0)) * (3.0 * delta ** 2.0))

    # multiply in white values
    xyz_array[:, 0] *= wht_x
    xyz_array[:, 1] *= wht_y
    xyz_array[:, 2] *= wht_z

    # convert to sRGB using the specified conversion matrix
    rgb_out = numpy.asarray(numpy.dot(xyz_array, conversionMatrix.T))

    # apply sRGB gamma correction if requested
    if transferFunc is not None:
        rgb_out = transferFunc(rgb_out, **kwargs)

    # clip unrepresentable colors if requested
    if clip:
        rgb_out = numpy.clip(rgb_out, 0.0, 1.0)

    # make the output match the dimensions/shape of input
    if orig_dim == 1:
        rgb_out = rgb_out[0]
    elif orig_dim == 3:
        rgb_out = numpy.reshape(rgb_out, orig_shape)

    return rgb_out * 2.0 - 1.0


def dkl2rgb(dkl, conversionMatrix=None):
    """Convert from DKL color space (Derrington, Krauskopf & Lennie) to RGB.

    Requires a conversion matrix, which will be generated from generic
    Sony Trinitron phosphors if not supplied (note that this will not be
    an accurate representation of the color space unless you supply a
    conversion matrix).

    usage::

        rgb(Nx3) = dkl2rgb(dkl_Nx3(el,az,radius), conversionMatrix)
        rgb(NxNx3) = dkl2rgb(dkl_NxNx3(el,az,radius), conversionMatrix)

    """
    if conversionMatrix is None:
        conversionMatrix = numpy.asarray([
            # (note that dkl has to be in cartesian coords first!)
            # LUMIN    %L-M    %L+M-S
            [1.0000, 1.0000, -0.1462],  # R
            [1.0000, -0.3900, 0.2094],  # G
            [1.0000, 0.0180, -1.0000]])  # B
        logging.warning('This monitor has not been color-calibrated. '
                        'Using default DKL conversion matrix.')

    if len(dkl.shape) == 3:
        dkl_NxNx3 = dkl
        # convert a 2D (image) of Spherical DKL colours to RGB space
        origShape = dkl_NxNx3.shape  # remember for later
        NxN = origShape[0] * origShape[1]  # find nPixels
        dkl = numpy.reshape(dkl_NxNx3, [NxN, 3])  # make Nx3
        rgb = dkl2rgb(dkl, conversionMatrix)  # convert
        return numpy.reshape(rgb, origShape)  # reshape and return

    else:
        dkl_Nx3 = dkl
        # its easier to use in the other orientation!
        dkl_3xN = numpy.transpose(dkl_Nx3)
        if numpy.size(dkl_3xN) == 3:
            RG, BY, LUM = sph2cart(dkl_3xN[0],
                                   dkl_3xN[1],
                                   dkl_3xN[2])
        else:
            RG, BY, LUM = sph2cart(dkl_3xN[0, :],
                                   dkl_3xN[1, :],
                                   dkl_3xN[2, :])
        dkl_cartesian = numpy.asarray([LUM, RG, BY])
        rgb = numpy.dot(conversionMatrix, dkl_cartesian)

        # return in the shape we received it:
        return numpy.transpose(rgb)


def dklCart2rgb(LUM, LM, S, conversionMatrix=None):
    """Like dkl2rgb except that it uses cartesian coords (LM,S,LUM)
    rather than spherical coords for DKL (elev, azim, contr).

    NB: this may return rgb values >1 or <-1
    """
    NxNx3 = list(LUM.shape)
    NxNx3.append(3)
    dkl_cartesian = numpy.asarray(
        [LUM.reshape([-1]), LM.reshape([-1]), S.reshape([-1])])

    if conversionMatrix is None:
        conversionMatrix = numpy.asarray([
            # (note that dkl has to be in cartesian coords first!)
            # LUMIN    %L-M    %L+M-S
            [1.0000, 1.0000, -0.1462],  # R
            [1.0000, -0.3900, 0.2094],  # G
            [1.0000, 0.0180, -1.0000]])  # B
    rgb = numpy.dot(conversionMatrix, dkl_cartesian)
    return numpy.reshape(numpy.transpose(rgb), NxNx3)


def hsv2rgb(hsv_Nx3):
    """Convert from HSV color space to RGB gun values.

    usage::

        rgb_Nx3 = hsv2rgb(hsv_Nx3)

    Note that in some uses of HSV space the Hue component is given in
    radians or cycles (range 0:1]). In this version H is given in
    degrees (0:360).

    Also note that the RGB output ranges -1:1, in keeping with other
    PsychoPy functions.
    """
    # based on method in
    # http://en.wikipedia.org/wiki/HSL_and_HSV#Converting_to_RGB

    hsv_Nx3 = numpy.asarray(hsv_Nx3, dtype=float)
    # we expect a 2D array so convert there if needed
    origShape = hsv_Nx3.shape
    hsv_Nx3 = hsv_Nx3.reshape([-1, 3])

    H_ = old_div((hsv_Nx3[:, 0] % 360), 60.0)  # this is H' in the wikipedia version
    # multiply H and V to give chroma (color intensity)
    C = hsv_Nx3[:, 1] * hsv_Nx3[:, 2]
    X = C * (1 - abs(H_ % 2 - 1))

    # rgb starts
    rgb = hsv_Nx3 * 0  # only need to change things that are no longer zero
    II = (0 <= H_) * (H_ < 1)
    rgb[II, 0] = C[II]
    rgb[II, 1] = X[II]
    II = (1 <= H_) * (H_ < 2)
    rgb[II, 0] = X[II]
    rgb[II, 1] = C[II]
    II = (2 <= H_) * (H_ < 3)
    rgb[II, 1] = C[II]
    rgb[II, 2] = X[II]
    II = (3 <= H_) * (H_ < 4)
    rgb[II, 1] = X[II]
    rgb[II, 2] = C[II]
    II = (4 <= H_) * (H_ < 5)
    rgb[II, 0] = X[II]
    rgb[II, 2] = C[II]
    II = (5 <= H_) * (H_ < 6)
    rgb[II, 0] = C[II]
    rgb[II, 2] = X[II]
    m = (hsv_Nx3[:, 2] - C)
    rgb += m.reshape([len(m), 1])  # V-C is sometimes called m
    return rgb.reshape(origShape) * 2 - 1


def lms2rgb(lms_Nx3, conversionMatrix=None):
    """Convert from cone space (Long, Medium, Short) to RGB.

    Requires a conversion matrix, which will be generated from generic
    Sony Trinitron phosphors if not supplied (note that you will not get
    an accurate representation of the color space unless you supply a
    conversion matrix)

    usage::

        rgb_Nx3 = lms2rgb(dkl_Nx3(el,az,radius), conversionMatrix)

    """

    # its easier to use in the other orientation!
    lms_3xN = numpy.transpose(lms_Nx3)

    if conversionMatrix is None:
        cones_to_rgb = numpy.asarray([
            # L        M        S
            [4.97068857, -4.14354132, 0.17285275],  # R
            [-0.90913894, 2.15671326, -0.24757432],  # G
            [-0.03976551, -0.14253782, 1.18230333]])  # B

        logging.warning('This monitor has not been color-calibrated. '
                        'Using default LMS conversion matrix.')
    else:
        cones_to_rgb = conversionMatrix

    rgb = numpy.dot(cones_to_rgb, lms_3xN)
    return numpy.transpose(rgb)  # return in the shape we received it


def rgb2dklCart(picture, conversionMatrix=None):
    """Convert an RGB image into Cartesian DKL space.
    """
    # Turn the picture into an array so we can do maths
    picture = numpy.array(picture)
    # Find the original dimensions of the picture
    origShape = picture.shape

    # this is the inversion of the dkl2rgb conversion matrix
    if conversionMatrix is None:
        conversionMatrix = numpy.asarray([
            # LUMIN->    %L-M->        L+M-S
            [0.25145542, 0.64933633, 0.09920825],
            [0.78737943, -0.55586618, -0.23151325],
            [0.26562825, 0.63933074, -0.90495899]])
        logging.warning('This monitor has not been color-calibrated. '
                        'Using default DKL conversion matrix.')
    else:
        conversionMatrix = numpy.linalg.inv(conversionMatrix)

    # Reshape the picture so that it can multiplied by the conversion matrix
    red = picture[:, :, 0]
    green = picture[:, :, 1]
    blue = picture[:, :, 2]

    dkl = numpy.asarray([red.reshape([-1]),
                         green.reshape([-1]),
                         blue.reshape([-1])])

    # Multiply the picture by the conversion matrix
    dkl = numpy.dot(conversionMatrix, dkl)

    # Reshape the picture so that it's back to it's original shape
    dklPicture = numpy.reshape(numpy.transpose(dkl), origShape)
    return dklPicture


def rgb2lms(rgb_Nx3, conversionMatrix=None):
    """Convert from RGB to cone space (LMS).

    Requires a conversion matrix, which will be generated from generic
    Sony Trinitron phosphors if not supplied (note that you will not get
    an accurate representation of the color space unless you supply a
    conversion matrix)

    usage::

        lms_Nx3 = rgb2lms(rgb_Nx3(el,az,radius), conversionMatrix)

    """

    # its easier to use in the other orientation!
    rgb_3xN = numpy.transpose(rgb_Nx3)

    if conversionMatrix is None:
        cones_to_rgb = numpy.asarray([
            # L        M        S
            [4.97068857, -4.14354132, 0.17285275],  # R
            [-0.90913894, 2.15671326, -0.24757432],  # G
            [-0.03976551, -0.14253782, 1.18230333]])  # B

        logging.warning('This monitor has not been color-calibrated. '
                        'Using default LMS conversion matrix.')
    else:
        cones_to_rgb = conversionMatrix
    rgb_to_cones = numpy.linalg.inv(cones_to_rgb)

    lms = numpy.dot(rgb_to_cones, rgb_3xN)
    return numpy.transpose(lms)  # return in the shape we received it
