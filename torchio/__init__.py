"""Top-level package for torchio."""

__author__ = """Fernando Perez-Garcia"""
__email__ = 'fernando.perezgarcia.17@ucl.ac.uk'
<<<<<<< HEAD
__version__ = '0.17.45'
=======
__version__ = '0.17.46'
>>>>>>> 3f98bcf00e4d004418f21f0cdb5282bee77fada3

import os
from . import utils
from .torchio import *
from .transforms import *
from .data import (
    io,
    sampler,
    inference,
    ImagesDataset,
    SubjectsDataset,
    Image,
    ScalarImage,
    LabelMap,
    Queue,
    Subject,
)
from . import datasets
from . import reference

CITATION = """If you use TorchIO for your research, please cite the following paper:
Pérez-García et al., TorchIO: a Python library for efficient loading,
preprocessing, augmentation and patch-based sampling of medical images
in deep learning. Credits instructions: https://torchio.readthedocs.io/#credits
"""

# Thanks for citing torchio. Without citations, researchers will not use TorchIO
if 'TORCHIO_HIDE_CITATION_PROMPT' not in os.environ:
    print(CITATION)  # noqa: T001
