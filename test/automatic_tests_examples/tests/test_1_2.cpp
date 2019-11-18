#include <mylib/lib.hpp>

#include <catch2/catch.hpp>

TEST_CASE( "first", "[1]" )
{
    SECTION( "2" )
    {
        REQUIRE( mylib::magic_function(1, 2) == 5 );
    }

    SECTION( "3" )
    {
        REQUIRE( mylib::magic_function(1, 3) == 7 );
    }
}