.. Clang Build documentation master file, created by
   sphinx-quickstart on Mon Jun  4 23:39:00 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Clang Build's documentation!
=======================================

Clang Build is a C++ build tool written in Python using the clang compiler. The code is open
source and `available on GitHub <https://github.com/Trick-17/clang-build>`_. Clang Build is
a system that tries its best to make the compile configuration process less of a pain.
The design goals to achive this were:

- Cross platform
    - One compiler (clang)
    - One build system (written in Python)
- Always hide as much complexity as possible
    - Simple projects should be simple
    - Build process for reasonable project structures should still be easy

If you want to know how you can use Clang Build to compile your project, you can have a look
at the user's guide which demonstrates the features of Clang Build in a series of examples.
If you want to have a look at how the python code of Clang Build is structured you can have a
look at the source code on GitHub or the code documentation in the second section of this
documentation.


.. toctree::
   :maxdepth: 5
   :caption: Contents:

   user_guide/user_guide.rst
   code_documentation/code_documentation.rst





.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
