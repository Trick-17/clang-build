#include <iostream>

#include <mylib.hpp>

int main(int argc, char ** argv)
{
    std::cerr << "Hello! mylib::triple(3) returned " << mylib::triple(3) << std::endl;
    return 0;
}