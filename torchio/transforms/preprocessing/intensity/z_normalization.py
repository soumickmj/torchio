import torch
from typing import Optional, List
from ....data.subject import Subject
from ....torchio import DATA
from .normalization_transform import NormalizationTransform, TypeMaskingMethod


class ZNormalization(NormalizationTransform):
    """Subtract mean and divide by standard deviation.

    Args:
        masking_method: See
            :py:class:`~torchio.transforms.preprocessing.intensity.normalization_transform.NormalizationTransform`.
        p: Probability that this transform will be applied.
        keys: See :py:class:`~torchio.transforms.Transform`.
    """
    def __init__(
            self,
            masking_method: TypeMaskingMethod = None,
            p: float = 1,
            keys: Optional[List[str]] = None,
            ):
        super().__init__(masking_method=masking_method, p=p, keys=keys)

    def apply_normalization(
            self,
            subject: Subject,
            image_name: str,
            mask: torch.Tensor,
            ) -> None:
        image = subject[image_name]
        standardized = self.znorm(
            image[DATA],
            mask,
        )
        if standardized is None:
            message = (
                'Standard deviation is 0 for masked values'
                f' in image "{image_name}" ({image.path})'
            )
            raise RuntimeError(message)
        image[DATA] = standardized

    @staticmethod
    def znorm(tensor: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        tensor = tensor.clone()
        values = tensor.masked_select(mask)
        mean, std = values.mean(), values.std()
        if std == 0:
            return None
        tensor -= mean
        tensor /= std
        return tensor
