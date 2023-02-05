module;

#include <iostream>

export module test;

namespace test {

// Functions like this need to be explicitly marked for export.
export void hello() { std::cout << "Hello World" << std::endl; }

} // namespace test