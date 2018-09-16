#include <iostream>
#include "version.h"

int main()
{
    std::cerr << "the version is " << VERSION_MAJOR << "." << VERSION_MINOR << "." << VERSION_PATCH << std::endl;
    return 0;
}