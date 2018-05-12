#pragma once

namespace the_lib
{
    template <typename T>
    T magic_function(const T& t1, const T& t2)
    {
        return t1 + 2 * t2;
    }
}