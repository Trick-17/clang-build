#include <iostream>

#include <mylib.hpp>

int main(int argc, char ** argv)
{
    std::cerr << "Hello! mylib::calculate() returned " << mylib::calculate() << std::endl;
    return 0;
}