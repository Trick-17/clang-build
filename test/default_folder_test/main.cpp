#include <iostream>
#include <smallfunctions.hpp>

int main(int argc, char ** argv)
{
    std::cerr << "Calculated Integer: " << calculateInt() << std::endl;
    std::cerr << "Calculated Vector:  " << calculateVec().transpose() << std::endl;
    return 0;
}