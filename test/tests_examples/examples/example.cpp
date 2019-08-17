#include <mylib/lib.hpp>

#include <iostream>

int main()
{
    std::cerr << "This is an example of using mylib:\n";
    std::cerr << "Calling `mylib::magic_function(1, 2)` returns `" << mylib::magic_function(1, 2) << "`\n";
}