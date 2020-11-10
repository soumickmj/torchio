from typing import Tuple, Optional, Union, List
import torch
from ....torchio import DATA
from ....data.subject import Subject
from ... import IntensityTransform
from .. import RandomTransform


class RandomNoise(RandomTransform, IntensityTransform):
    r"""Add random Gaussian noise.

    Add noise sampled from a normal distribution.

    Args:
        mean: Mean :math:`\mu` of the Gaussian distribution
            from which the noise is sampled.
            If two values :math:`(a, b)` are provided,
            then :math:`\mu \sim \mathcal{U}(a, b)`.
            If only one value :math:`d` is provided,
            :math:`\mu \sim \mathcal{U}(-d, d)`.
        std: Standard deviation :math:`\sigma` of the Gaussian distribution
            from which the noise is sampled.
            If two values :math:`(a, b)` are provided,
            then :math:`\sigma \sim \mathcal{U}(a, b)`.
            If only one value :math:`d` is provided,
            :math:`\sigma \sim \mathcal{U}(0, d)`.
        p: Probability that this transform will be applied.
        seed: See :py:class:`~torchio.transforms.augmentation.RandomTransform`.
        keys: See :py:class:`~torchio.transforms.Transform`.
    """
    def __init__(
            self,
            mean: Union[float, Tuple[float, float]] = 0,
            std: Union[float, Tuple[float, float]] = (0, 0.25),
            p: float = 1,
            keys: Optional[List[str]] = None,
            ):
        super().__init__(p=p, keys=keys)
        self.mean_range = self.parse_range(mean, 'mean')
        self.std_range = self.parse_range(std, 'std', min_constraint=0)

    def apply_transform(self, subject: Subject) -> Subject:
        random_parameters_images_dict = {}
        for image_name, image_dict in self.get_images_dict(subject).items():
            mean, std = self.get_params(self.mean_range, self.std_range)
            random_parameters_dict = {'std': std}
            random_parameters_images_dict[image_name] = random_parameters_dict
            image_dict[DATA] = add_noise(image_dict[DATA], mean, std)
        return subject

    @staticmethod
    def get_params(
            mean_range: Tuple[float, float],
            std_range: Tuple[float, float],
            ) -> Tuple[float, float]:
        mean = torch.FloatTensor(1).uniform_(*mean_range).item()
        std = torch.FloatTensor(1).uniform_(*std_range).item()
        return mean, std


def add_noise(tensor: torch.Tensor, mean: float, std: float) -> torch.Tensor:
    noise = torch.randn(*tensor.shape) * std + mean
    tensor = tensor + noise
    return tensor
