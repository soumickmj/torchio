from numbers import Number
from typing import Tuple, Optional, List, Union
import torch
import numpy as np
import SimpleITK as sitk
from ....data.subject import Subject
from ....utils import nib_to_sitk, get_major_sitk_version, to_tuple
from ....torchio import (
    INTENSITY,
    DATA,
    AFFINE,
    TYPE,
    TypeRangeFloat,
    TypeSextetFloat,
    TypeTripletFloat,
)
from ... import SpatialTransform
from .. import Interpolation, get_sitk_interpolator
from .. import RandomTransform


TypeOneToSixFloat = Union[TypeRangeFloat, TypeTripletFloat, TypeSextetFloat]


class RandomAffine(RandomTransform, SpatialTransform):
    r"""Random affine transformation.

    Args:
        scales: Tuple :math:`(a_1, b_1, a_2, b_2, a_3, b_3)` defining the
            scaling ranges.
            The scaling values along each dimension are :math:`(s_1, s_2, s_3)`,
            where :math:`s_i \sim \mathcal{U}(a_i, b_i)`.
            If two values :math:`(a, b)` are provided,
            then :math:`s_i \sim \mathcal{U}(a, b)`.
            If only one value :math:`x` is provided,
            then :math:`s_i \sim \mathcal{U}(1 - x, 1 + x)`.
            If three values :math:`(x_1, x_2, x_3)` are provided,
            then :math:`s_i \sim \mathcal{U}(1 - x_i, 1 + x_i)`.
            For example, using ``scales=(0.5, 0.5)`` will zoom out the image,
            making the objects inside look twice as small while preserving
            the physical size and position of the image bounds.
        degrees: Tuple :math:`(a_1, b_1, a_2, b_2, a_3, b_3)` defining the
            rotation ranges in degrees.
            Rotation angles around each axis are
            :math:`(\theta_1, \theta_2, \theta_3)`,
            where :math:`\theta_i \sim \mathcal{U}(a_i, b_i)`.
            If two values :math:`(a, b)` are provided,
            then :math:`\theta_i \sim \mathcal{U}(a, b)`.
            If only one value :math:`x` is provided,
            then :math:`\theta_i \sim \mathcal{U}(-x, x)`.
            If three values :math:`(x_1, x_2, x_3)` are provided,
            then :math:`\theta_i \sim \mathcal{U}(-x_i, x_i)`.
        translation: Tuple :math:`(a_1, b_1, a_2, b_2, a_3, b_3)` defining the
            translation ranges in mm.
            Translation along each axis is :math:`(t_1, t_2, t_3)`,
            where :math:`t_i \sim \mathcal{U}(a_i, b_i)`.
            If two values :math:`(a, b)` are provided,
            then :math:`t_i \sim \mathcal{U}(a, b)`.
            If only one value :math:`x` is provided,
            then :math:`t_i \sim \mathcal{U}(-x, x)`.
            If three values :math:`(x_1, x_2, x_3)` are provided,
            then :math:`t_i \sim \mathcal{U}(-x_i, x_i)`.
        isotropic: If ``True``, the scaling factor along all dimensions is the
            same, i.e. :math:`s_1 = s_2 = s_3`.
        center: If ``'image'``, rotations and scaling will be performed around
            the image center. If ``'origin'``, rotations and scaling will be
            performed around the origin in world coordinates.
        default_pad_value: As the image is rotated, some values near the
            borders will be undefined.
            If ``'minimum'``, the fill value will be the image minimum.
            If ``'mean'``, the fill value is the mean of the border values.
            If ``'otsu'``, the fill value is the mean of the values at the
            border that lie under an
            `Otsu threshold <https://ieeexplore.ieee.org/document/4310076>`_.
            If it is a number, that value will be used.
        image_interpolation: See :ref:`Interpolation`.
        p: Probability that this transform will be applied.
        seed: See :py:class:`~torchio.transforms.augmentation.RandomTransform`.
        keys: See :py:class:`~torchio.transforms.Transform`.

    Example:
        >>> import torchio as tio
        >>> subject = tio.datasets.Colin27()
        >>> transform = tio.RandomAffine(
        ...     scales=(0.9, 1.2),
        ...     degrees=(10),
        ...     isotropic=False,
        ...     default_pad_value='otsu',
        ...     image_interpolation='bspline',
        ... )
        >>> transformed = transform(subject)

    From the command line::

        $ torchio-transform t1.nii.gz RandomAffine --kwargs "degrees=30 default_pad_value=minimum" --seed 42 affine_min.nii.gz

    """
    def __init__(
            self,
            scales: TypeOneToSixFloat = 0.1,
            degrees: TypeOneToSixFloat = 10,
            translation: TypeOneToSixFloat = 0,
            isotropic: bool = False,
            center: str = 'image',
            default_pad_value: Union[str, float] = 'otsu',
            image_interpolation: str = 'linear',
            p: float = 1,
            keys: Optional[List[str]] = None,
            ):
        super().__init__(p=p, keys=keys)
        self.isotropic = isotropic
        self.parse_scales_isotropic(scales, isotropic)
        self.scales = self.parse_params(scales, 1, 'scales', min_constraint=0)
        self.degrees = self.parse_params(degrees, 0, 'degrees')
        self.translation = self.parse_params(translation, 0, 'translation')
        if center not in ('image', 'origin'):
            message = (
                'Center argument must be "image" or "origin",'
                f' not "{center}"'
            )
            raise ValueError(message)
        self.use_image_center = center == 'image'
        self.default_pad_value = self.parse_default_value(default_pad_value)
        self.interpolation = self.parse_interpolation(image_interpolation)

    @staticmethod
    def parse_scales_isotropic(scales, isotropic):
        params = to_tuple(scales)
        if isotropic and len(scales) in (3, 6):
            message = (
                'If "isotropic" is True, the value for "scales" must have'
                f' length 1 or 2, but "{scales}" was passed'
            )
            raise ValueError(message)

    @staticmethod
    def parse_default_value(value: Union[str, float]) -> Union[str, float]:
        if isinstance(value, Number) or value in ('minimum', 'otsu', 'mean'):
            return value
        message = (
            'Value for default_pad_value must be "minimum", "otsu", "mean"'
            ' or a number'
        )
        raise ValueError(message)

    def get_params(
            self,
            scales: TypeSextetFloat,
            degrees: TypeSextetFloat,
            translation: TypeSextetFloat,
            isotropic: bool,
            ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        scaling_params = self.sample_uniform_sextet(scales)
        if isotropic:
            scaling_params.fill_(scaling_params[0])
        rotation_params = self.sample_uniform_sextet(degrees)
        translation_params = self.sample_uniform_sextet(translation)
        return scaling_params, rotation_params, translation_params

    @staticmethod
    def get_scaling_transform(
            scaling_params: List[float],
            center_lps: Optional[TypeTripletFloat] = None,
            ) -> sitk.ScaleTransform:
        # scaling_params are inverted so that they are more intuitive
        # For example, 1.5 means the objects look 1.5 times larger
        transform = sitk.ScaleTransform(3)
        scaling_params = 1 / np.array(scaling_params)
        transform.SetScale(scaling_params)
        if center_lps is not None:
            transform.SetCenter(center_lps)
        return transform

    @staticmethod
    def get_rotation_transform(
            degrees: List[float],
            translation: List[float],
            center_lps: Optional[TypeTripletFloat] = None,
            ) -> sitk.Euler3DTransform:
        transform = sitk.Euler3DTransform()
        radians = np.radians(degrees)
        transform.SetRotation(*radians)
        transform.SetTranslation(translation)
        if center_lps is not None:
            transform.SetCenter(center_lps)
        return transform

    def apply_transform(self, subject: Subject) -> Subject:
        subject.check_consistent_spatial_shape()
        scaling_params, rotation_params, translation_params = self.get_params(
            self.scales,
            self.degrees,
            self.translation,
            self.isotropic,
        )
        for image in self.get_images(subject):
            if image[TYPE] != INTENSITY:
                interpolation = Interpolation.NEAREST
            else:
                interpolation = self.interpolation

            if image.is_2d():
                scaling_params[2] = 1
                rotation_params[:-1] = 0

            if self.use_image_center:
                center = image.get_center(lps=True)
            else:
                center = None

            transformed_tensors = []
            for tensor in image[DATA]:
                transformed_tensor = self.apply_affine_transform(
                    tensor,
                    image[AFFINE],
                    scaling_params.tolist(),
                    rotation_params.tolist(),
                    translation_params.tolist(),
                    interpolation,
                    center_lps=center,
                )
                transformed_tensors.append(transformed_tensor)
            image[DATA] = torch.stack(transformed_tensors)
        random_parameters_dict = {
            'scaling': scaling_params,
            'rotation': rotation_params,
            'translation': translation_params,
        }
        return subject

    def apply_affine_transform(
            self,
            tensor: torch.Tensor,
            affine: np.ndarray,
            scaling_params: List[float],
            rotation_params: List[float],
            translation_params: List[float],
            interpolation: Interpolation,
            center_lps: Optional[TypeTripletFloat] = None,
            ) -> torch.Tensor:
        assert tensor.ndim == 3

        image = nib_to_sitk(tensor[np.newaxis], affine, force_3d=True)
        floating = reference = image

        scaling_transform = self.get_scaling_transform(
            scaling_params,
            center_lps=center_lps,
        )
        rotation_transform = self.get_rotation_transform(
            rotation_params,
            translation_params,
            center_lps=center_lps,
        )

        sitk_major_version = get_major_sitk_version()
        if sitk_major_version == 1:
            transform = sitk.Transform(3, sitk.sitkComposite)
            transform.AddTransform(scaling_transform)
            transform.AddTransform(rotation_transform)
        elif sitk_major_version == 2:
            transforms = [scaling_transform, rotation_transform]
            transform = sitk.CompositeTransform(transforms)

        if self.default_pad_value == 'minimum':
            default_value = tensor.min().item()
        elif self.default_pad_value == 'mean':
            default_value = get_borders_mean(image, filter_otsu=False)
        elif self.default_pad_value == 'otsu':
            default_value = get_borders_mean(image, filter_otsu=True)
        else:
            default_value = self.default_pad_value

        resampler = sitk.ResampleImageFilter()
        resampler.SetInterpolator(get_sitk_interpolator(interpolation))
        resampler.SetReferenceImage(reference)
        resampler.SetDefaultPixelValue(float(default_value))
        resampler.SetOutputPixelType(sitk.sitkFloat32)
        resampler.SetTransform(transform)
        resampled = resampler.Execute(floating)

        np_array = sitk.GetArrayFromImage(resampled)
        np_array = np_array.transpose()  # ITK to NumPy
        tensor = torch.from_numpy(np_array)
        return tensor

# flake8: noqa: E201, E203, E243
def get_borders_mean(image, filter_otsu=True):
    # pylint: disable=bad-whitespace
    array = sitk.GetArrayViewFromImage(image)
    borders_tuple = (
        array[ 0,  :,  :],
        array[-1,  :,  :],
        array[ :,  0,  :],
        array[ :, -1,  :],
        array[ :,  :,  0],
        array[ :,  :, -1],
    )
    borders_flat = np.hstack([border.ravel() for border in borders_tuple])
    if not filter_otsu:
        return borders_flat.mean()
    borders_reshaped = borders_flat.reshape(1, 1, -1)
    borders_image = sitk.GetImageFromArray(borders_reshaped)
    otsu = sitk.OtsuThresholdImageFilter()
    otsu.Execute(borders_image)
    threshold = otsu.GetThreshold()
    values = borders_flat[borders_flat < threshold]
    if values.any():
        default_value = values.mean()
    else:
        default_value = borders_flat.mean()
    return default_value
