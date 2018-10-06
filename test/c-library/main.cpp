#include <iostream>
#include <array>
#include <vector>

#include <libqhullcpp/Qhull.h>
#include <libqhullcpp/QhullFacetList.h>
#include <libqhullcpp/QhullVertexSet.h>


typedef std::array<int, 3> triangle_t;
typedef struct {
    double x, y;
} vector2_t;


std::vector<triangle_t> compute_delaunay_triangulation_2D(const std::vector<vector2_t> & points)
{
    const int ndim = 2;
    std::vector<triangle_t> triangles;
    triangle_t tmp_triangle;
    int *current_index;

    orgQhull::Qhull qhull;
    qhull.runQhull("", ndim, points.size(), (coordT *) points.data(),  "d Qt Qbb Qz");
    for(const auto & facet : qhull.facetList())
    {
        if(!facet.isUpperDelaunay())
        {
            current_index = &tmp_triangle[0];
            for(const auto & vertex : facet.vertices())
            {
                *current_index++ = vertex.point().id();
            }
            triangles.push_back(tmp_triangle);
        }
    }
    return triangles;
}


int main()
{
    std::vector<vector2_t> points{{0, 0}, {1, 0}, {0, 1}, {1, 1}};
    auto triangles = compute_delaunay_triangulation_2D(points);
    for( auto& tri : triangles )
        std::cerr << tri[0] << " " << tri[1] << " " << tri[2] << std::endl;
}