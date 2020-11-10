.. _Getting started:

###############
Getting started
###############

Installation
============

The Python package is hosted on the
`Python Package Index (PyPI) <https://pypi.org/project/torchio/>`_.

The latest published version can be installed
using Pip Installs Packages (``pip``)::

    $ pip install torchio

To upgrade to the latest published version, use::

    $ pip install --upgrade torchio

If you are on Windows and have
`trouble installing TorchIO<https://github.com/fepegar/torchio/issues/343>`_,
try `installing PyTorch <https://pytorch.org/get-started/locally/>`_ with
`conda <https://docs.conda.io/en/latest/miniconda.html>`_ before pip-installing
TorchIO.

Hello, World!
=============

This example shows the basic usage of TorchIO, where an instance of
:py:class:`~torchio.data.dataset.SubjectsDataset` is passed to
a PyTorch :py:class:`~torch.utils.data.DataLoader` to generate training batches
of 3D images that are loaded, preprocessed and augmented on the fly,
in parallel::

    import torchio as tio
    from tio.transforms import (
        RescaleIntensity,
        RandomAffine,
        RandomElasticDeformation,
        Compose,
    )
    from torch.utils.data import DataLoader

    # Each instance of tio.Subject is passed arbitrary keyword arguments.
    # Typically, these arguments will be instances of tio.Image
    subject_a = tio.Subject(
        t1=tio.ScalarImage('subject_a.nii.gz'),
        label=tio.LabelMap('subject_a.nii'),
        diagnosis='positive',
    )

    # Images can be in any format supported by SimpleITK or NiBabel, including DICOM
    subject_b = tio.Subject(
        t1=tio.ScalarImage('subject_b_dicom_folder'),
        label=tio.LabelMap('subject_b_seg.nrrd'),
        diagnosis='negative',
    )
    subjects_list = [subject_a, subject_b]

    # Let's use one preprocessing transform and one augmentation transform
    # This transform will be applied only to scalar images:
    rescale = RescaleIntensity((0, 1))

    # As RandomAffine is faster then RandomElasticDeformation, we choose to
    # apply RandomAffine 80% of the times and RandomElasticDeformation the rest
    # Also, there is a 25% chance that none of them will be applied
    spatial = OneOf(
        {RandomAffine(): 0.8, RandomElasticDeformation(): 0.2},
        p=0.75,
    )

    # Transforms can be composed as in torchvision.transforms
    transforms = [rescale, spatial]
    transform = Compose(transforms)

    # SubjectsDataset is a subclass of torch.data.utils.Dataset
    subjects_dataset = tio.SubjectsDataset(subjects_list, transform=transform)

    # Images are processed in parallel thanks to a PyTorch DataLoader
    training_loader = DataLoader(subjects_dataset, batch_size=4, num_workers=4)

    # Training epoch
    for subjects_batch in training_loader:
        inputs = subjects_batch['t1'][tio.DATA]
        target = subjects_batch['label'][tio.DATA]




Google Colab Jupyter Notebooks
==============================

|Google-Colab-notebook|

The best way to quickly understand and try the library is the
`Jupyter Notebooks <https://github.com/fepegar/torchio/blob/master/examples/README.md>`_
hosted on Google Colab.

They include many examples and visualization of most of the classes and even
training of a `3D U-Net <https://www.github.com/fepegar/unet>`_ for brain
segmentation of :math:`T_1`-weighted MRI with full volumes and
with subvolumes (aka patches or windows).

.. |Google-Colab-notebook| image:: https://colab.research.google.com/assets/colab-badge.svg
   :target: https://github.com/fepegar/torchio/blob/master/examples/README.md
   :alt: Google Colab notebook
