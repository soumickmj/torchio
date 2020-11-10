from typing import Union, Tuple, Optional, List
import torch
from ....torchio import TypeRangeFloat
from ....data.subject import Subject
from ....utils import to_tuple
from ... import SpatialTransform
from .. import RandomTransform
from ...preprocessing import Resample


class RandomDownsample(RandomTransform, SpatialTransform):
    r"""Downsample an image along an axis.

    This transform simulates an image that has been acquired using anisotropic
    spacing, using downsampling with nearest neighbor interpolation.

    Args:
        axes: Axis or tuple of axes along which the image will be downsampled.
        downsampling: Downsampling factor :math:`m \gt 1`. If a tuple
            :math:`(a, b)` is provided then :math:`m \sim \mathcal{U}(a, b)`.
        p: Probability that this transform will be applied.
        seed: See :py:class:`~torchio.transforms.augmentation.RandomTransform`.
        keys: See :py:class:`~torchio.transforms.Transform`.

    Example:
        >>> import torchio as tio
        >>> transform = tio.RandomDownsample(axes=1, downsampling=2.)   # Multiply spacing of second axis by 2
        >>> transform = tio.RandomDownsample(
        ...     axes=(0, 1, 2),
        ...     downsampling=(2, 5),
        ... )   # Multiply spacing of one of the 3 axes by a factor randomly chosen in [2, 5]
        >>> colin = tio.datasets.Colin27()
        >>> transformed = transform(colin)  # images have now anisotropic spacing
    """

    def __init__(
            self,
            axes: Union[int, Tuple[int, ...]] = (0, 1, 2),
            downsampling: TypeRangeFloat = (1.5, 5),
            p: float = 1,
            keys: Optional[List[str]] = None,
            ):
        super().__init__(p=p, keys=keys)
        self.axes = self.parse_axes(axes)
        self.downsampling_range = self.parse_range(
            downsampling, 'downsampling', min_constraint=1)

    @staticmethod
    def get_params(
            axes: Tuple[int, ...],
            downsampling_range: Tuple[float, float],
            ) -> List[bool]:
        axis = axes[torch.randint(0, len(axes), (1,))]
        downsampling = torch.FloatTensor(1).uniform_(*downsampling_range).item()
        return axis, downsampling

    @staticmethod
    def parse_axes(axes: Union[int, Tuple[int, ...]]):
        axes_tuple = to_tuple(axes)
        for axis in axes_tuple:
            is_int = isinstance(axis, int)
            if not is_int or axis not in (0, 1, 2):
                raise ValueError('All axes must be 0, 1 or 2')
        return axes_tuple

    def apply_transform(self, subject: Subject) -> Subject:
        axis, downsampling = self.get_params(self.axes, self.downsampling_range)
        random_parameters_dict = {'axis': axis, 'downsampling': downsampling}

        target_spacing = list(subject.spacing)
        target_spacing[axis] *= downsampling
        transform = Resample(
            tuple(target_spacing),
            image_interpolation='nearest',
        )
        subject = transform(subject)
        return subject
