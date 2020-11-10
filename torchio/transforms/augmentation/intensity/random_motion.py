"""
Custom implementation of

    Shaw et al., 2019
    MRI k-Space Motion Artefact Augmentation:
    Model Robustness and Task-Specific Uncertainty

"""

from typing import Tuple, Optional, List
import torch
import numpy as np
import SimpleITK as sitk
from ....utils import nib_to_sitk
from ....torchio import DATA, AFFINE
from ....data.subject import Subject
from .. import Interpolation, get_sitk_interpolator
from ... import IntensityTransform
from .. import RandomTransform


class RandomMotion(RandomTransform, IntensityTransform):
    r"""Add random MRI motion artifact.

    Magnetic resonance images suffer from motion artifacts when the subject
    moves during image acquisition. This transform follows
    `Shaw et al., 2019 <http://proceedings.mlr.press/v102/shaw19a.html>`_ to
    simulate motion artifacts for data augmentation.

    Args:
        degrees: Tuple :math:`(a, b)` defining the rotation range in degrees of
            the simulated movements. The rotation angles around each axis are
            :math:`(\theta_1, \theta_2, \theta_3)`,
            where :math:`\theta_i \sim \mathcal{U}(a, b)`.
            If only one value :math:`d` is provided,
            :math:`\theta_i \sim \mathcal{U}(-d, d)`.
            Larger values generate more distorted images.
        translation: Tuple :math:`(a, b)` defining the translation in mm of
            the simulated movements. The translations along each axis are
            :math:`(t_1, t_2, t_3)`,
            where :math:`t_i \sim \mathcal{U}(a, b)`.
            If only one value :math:`t` is provided,
            :math:`t_i \sim \mathcal{U}(-t, t)`.
            Larger values generate more distorted images.
        num_transforms: Number of simulated movements.
            Larger values generate more distorted images.
        image_interpolation: See :ref:`Interpolation`.
        p: Probability that this transform will be applied.
        seed: See :py:class:`~torchio.transforms.augmentation.RandomTransform`.
        keys: See :py:class:`~torchio.transforms.Transform`.

    .. warning:: Large numbers of movements lead to longer execution times for
        3D images.
    """
    def __init__(
            self,
            degrees: float = 10,
            translation: float = 10,  # in mm
            num_transforms: int = 2,
            image_interpolation: str = 'linear',
            p: float = 1,
            keys: Optional[List[str]] = None,
            ):
        super().__init__(p=p, keys=keys)
        self.degrees_range = self.parse_degrees(degrees)
        self.translation_range = self.parse_translation(translation)
        if not 0 < num_transforms or not isinstance(num_transforms, int):
            message = (
                'Number of transforms must be a strictly positive natural'
                f'number, not {num_transforms}'
            )
            raise ValueError(message)
        self.num_transforms = num_transforms
        self.interpolation = self.parse_interpolation(image_interpolation)

    def apply_transform(self, subject: Subject) -> Subject:
        random_parameters_images_dict = {}
        for image_name, image in self.get_images_dict(subject).items():
            result_arrays = []
            for channel_idx, data in enumerate(image[DATA]):
                params = self.get_params(
                    self.degrees_range,
                    self.translation_range,
                    self.num_transforms,
                    is_2d=image.is_2d(),
                )
                times_params, degrees_params, translation_params = params
                random_parameters_dict = {
                    'times': times_params,
                    'degrees': degrees_params,
                    'translation': translation_params,
                }
                key = f'{image_name}_channel_{channel_idx}'
                random_parameters_images_dict[key] = random_parameters_dict
                sitk_image = nib_to_sitk(
                    data[np.newaxis],
                    image[AFFINE],
                    force_3d=True,
                )
                transforms = self.get_rigid_transforms(
                    degrees_params,
                    translation_params,
                    sitk_image,
                )
                data = self.add_artifact(
                    sitk_image,
                    transforms,
                    times_params,
                    self.interpolation,
                )
                result_arrays.append(data)
            result = np.stack(result_arrays)
            image[DATA] = torch.from_numpy(result)
        return subject

    @staticmethod
    def get_params(
            degrees_range: Tuple[float, float],
            translation_range: Tuple[float, float],
            num_transforms: int,
            perturbation: float = 0.3,
            is_2d: bool = False,
            ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        # If perturbation is 0, time intervals between movements are constant
        degrees_params = get_params_array(
            degrees_range, num_transforms)
        translation_params = get_params_array(
            translation_range, num_transforms)
        if is_2d:  # imagine sagittal (1, A, S)
            degrees_params[:, :-1] = 0  # rotate around Z axis only
            translation_params[:, 2] = 0  # translate in XY plane only
        step = 1 / (num_transforms + 1)
        times = torch.arange(0, 1, step)[1:]
        noise = torch.FloatTensor(num_transforms)
        noise.uniform_(-step * perturbation, step * perturbation)
        times += noise
        times_params = times.numpy()
        return times_params, degrees_params, translation_params

    def get_rigid_transforms(
            self,
            degrees_params: np.ndarray,
            translation_params: np.ndarray,
            image: sitk.Image,
            ) -> List[sitk.Euler3DTransform]:
        center_ijk = np.array(image.GetSize()) / 2
        center_lps = image.TransformContinuousIndexToPhysicalPoint(center_ijk)
        identity = np.eye(4)
        matrices = [identity]
        for degrees, translation in zip(degrees_params, translation_params):
            radians = np.radians(degrees).tolist()
            motion = sitk.Euler3DTransform()
            motion.SetCenter(center_lps)
            motion.SetRotation(*radians)
            motion.SetTranslation(translation.tolist())
            motion_matrix = self.transform_to_matrix(motion)
            matrices.append(motion_matrix)
        transforms = [self.matrix_to_transform(m) for m in matrices]
        return transforms

    @staticmethod
    def transform_to_matrix(transform: sitk.Euler3DTransform) -> np.ndarray:
        matrix = np.eye(4)
        rotation = np.array(transform.GetMatrix()).reshape(3, 3)
        matrix[:3, :3] = rotation
        matrix[:3, 3] = transform.GetTranslation()
        return matrix

    @staticmethod
    def matrix_to_transform(matrix: np.ndarray) -> sitk.Euler3DTransform:
        transform = sitk.Euler3DTransform()
        rotation = matrix[:3, :3].flatten().tolist()
        transform.SetMatrix(rotation)
        transform.SetTranslation(matrix[:3, 3])
        return transform

    @staticmethod
    def resample_images(
            image: sitk.Image,
            transforms: List[sitk.Euler3DTransform],
            interpolation: Interpolation,
            ) -> List[sitk.Image]:
        floating = reference = image
        default_value = np.float64(sitk.GetArrayViewFromImage(image).min())
        transforms = transforms[1:]  # first is identity
        images = [image]  # first is identity
        for transform in transforms:
            resampler = sitk.ResampleImageFilter()
            resampler.SetInterpolator(get_sitk_interpolator(interpolation))
            resampler.SetReferenceImage(reference)
            resampler.SetOutputPixelType(sitk.sitkFloat32)
            resampler.SetDefaultPixelValue(default_value)
            resampler.SetTransform(transform)
            resampled = resampler.Execute(floating)
            images.append(resampled)
        return images

    @staticmethod
    def sort_spectra(spectra: np.ndarray, times: np.ndarray):
        """Use original spectrum to fill the center of k-space"""
        num_spectra = len(spectra)
        if np.any(times > 0.5):
            index = np.where(times > 0.5)[0].min()
        else:
            index = num_spectra - 1
        spectra[0], spectra[index] = spectra[index], spectra[0]

    def add_artifact(
            self,
            image: sitk.Image,
            transforms: List[sitk.Euler3DTransform],
            times: np.ndarray,
            interpolation: Interpolation,
            ):
        images = self.resample_images(image, transforms, interpolation)
        arrays = [sitk.GetArrayViewFromImage(im) for im in images]
        arrays = [array.transpose() for array in arrays]  # ITK to NumPy
        spectra = [self.fourier_transform(array) for array in arrays]
        self.sort_spectra(spectra, times)
        result_spectrum = np.empty_like(spectra[0])
        last_index = result_spectrum.shape[2]
        indices = (last_index * times).astype(int).tolist()
        indices.append(last_index)
        ini = 0
        for spectrum, fin in zip(spectra, indices):
            result_spectrum[..., ini:fin] = spectrum[..., ini:fin]
            ini = fin
        result_image = np.real(self.inv_fourier_transform(result_spectrum))
        return result_image.astype(np.float32)


def get_params_array(nums_range: Tuple[float, float], num_transforms: int):
    tensor = torch.FloatTensor(num_transforms, 3).uniform_(*nums_range)
    return tensor.numpy()
