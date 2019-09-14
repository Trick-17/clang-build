#!/usr/bin/env python

import setuptools
from multiprocessing import freeze_support as _freeze_support

if __name__ == '__main__':
    _freeze_support()
    setuptools.setup(
        python_requires='>=3.7',
        setup_requires=['pbr<4'],
        pbr=True)
