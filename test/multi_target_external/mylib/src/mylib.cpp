#include <mylib.hpp>

#include <Eigen/Core>
#include <Eigen/Dense>

namespace mylib
{
    float calculate()
    {
        using Eigen::Vector3f;
        return Vector3f{1,0,0}.cross(Vector3f{0,1,0}).dot(Vector3f{0,0,2});
    }
}