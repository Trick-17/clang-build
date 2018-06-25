#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>

#include <mylib.hpp>

#include <memory>

namespace py = pybind11;

PYBIND11_MODULE(pylib, m)
{
    m.attr("__version__") = "dev";

    // Module docstring
    m.doc() = "This is my library...";

    // Module functions
    m.def("triple", &mylib::triple, "calculate the triple of a number");
}