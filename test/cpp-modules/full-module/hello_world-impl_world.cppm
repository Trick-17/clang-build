module;

#include <iostream>
#include <string>

module hello_world:impl_world;
import :world;

std::string w = "World.";

void World()
{
    std::cout << w << std::endl;
}
