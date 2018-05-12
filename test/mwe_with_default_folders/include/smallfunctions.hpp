#pragma once

#include <ExternalLib/super_useful_header.hpp>

int calculate_magic()
{
    int number = 22;
    return the_lib::magic_function<int>(number, 4);
}