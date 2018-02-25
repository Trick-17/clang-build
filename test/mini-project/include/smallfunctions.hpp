#pragma once

#include <Eigen/Core>
#include <Eigen/Dense>

int calculateInt()
{
    int number = 22;
    for (int i=1; i<20; ++i)
    {
        number = i * number / 4;
    }
    return number;
}

Eigen::Vector3f calculateVec()
{
    auto x = Eigen::Vector3f{1, 0, 0};
    auto y = Eigen::Vector3f{0, 1, 0};
    return x.cross(y);
}