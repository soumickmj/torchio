#############
3D Slicer GUI
#############

`3D Slicer <https://www.slicer.org/>`_ is an open-source software platform for
medical image informatics, image processing,
and three-dimensional visualization.

You can download and install Slicer 4.11 from
`their download website <https://www.download.slicer.org/>`_ or, if you are on
macOS, using `Homebrew <https://docs.brew.sh/>`_:
``brew cask install slicer-nightly``.

TorchIO provides a 3D Slicer extension for quick experimentation and
visualization of the package features without any coding.

The TorchIO extension can be easily installed using the
`Extensions Manager <https://www.slicer.org/wiki/Documentation/4.10/SlicerApplication/ExtensionsManager>`_.

The code and installation instructions are available on
`GitHub <https://github.com/fepegar/SlicerTorchIO>`_.

Modules
=======

TorchIO Transforms
------------------

This module can be used to quickly visualize the effect of each transform
parameter.
That way, users can have an intuitive feeling of what the output
of a transform looks like without any coding at all.

.. image:: https://raw.githubusercontent.com/fepegar/SlicerTorchIO/master/Screenshots/TorchIO.png
    :alt: TorchIO Transforms module for 3D Slicer


Usage example
^^^^^^^^^^^^^

Go to the ``Sample Data`` module to get an image we can use:

.. image:: https://raw.githubusercontent.com/fepegar/SlicerTorchIO/master/Screenshots/usage_1.png
    :alt: Go to Sample Data module


Click on an image to download, for example MRHead [#]_,
and go to the ``TorchIO Transforms`` module:

.. [#] All the data in ``Sample Data`` can be downloaded and used in the TorchIO
    Python library using the :py:class:`torchio.datasets.slicer.Slicer` class.

.. image:: https://raw.githubusercontent.com/fepegar/SlicerTorchIO/master/Screenshots/usage_2.png
    :alt: Download MRHead and go to TorchIO Transforms module


Select the input and output volume nodes:

.. image:: https://raw.githubusercontent.com/fepegar/SlicerTorchIO/master/Screenshots/usage_3.png
    :alt: Select volume nodes


Modify the transform parameters and click on ``Apply transform``.
Hovering the mouse over the transforms will show tooltips extracted from the
TorchIO documentation.

.. image:: https://raw.githubusercontent.com/fepegar/SlicerTorchIO/master/Screenshots/usage_4.png
    :alt: Select volume nodes


You can click on the ``Toggle volumes`` button to switch between input and output
volumes.
