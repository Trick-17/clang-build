#pragma once

#include <string>
#include <Eigen/Core>

std::string main_print()
{
    float norm = Eigen::Vector3f{0,1,2}.norm();
    return  "Hello! Eigen::Vector3f{0,1,2}.norm()=" + std::to_string(norm);
}