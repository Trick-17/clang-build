#include <mylib.hpp>

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>

#include <memory>

namespace py = pybind11;

PYBIND11_MODULE(pylib, m)
{
    // Module version info
    m.attr("__version__") = "0.0.1dev";

    // Module docstring
    m.doc() = "This is my library...";

    // Module functions
    m.def("triple", &mylib::triple, "calculate the triple of a number");
}