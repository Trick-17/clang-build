#include <iostream>

extern "C"
void print_hi()
{
    std::cout << "hello from function!\n";
}

extern "C"
float return_x()
{
    return 3.0;
}