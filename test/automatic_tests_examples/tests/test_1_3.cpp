#include <mylib/lib.hpp>

#include <catch2/catch.hpp>

TEST_CASE( "second", "[2]" )
{
    SECTION( "5" )
    {
        REQUIRE( mylib::magic_function(2, 5) == 12 );
    }

    SECTION( "6" )
    {
        REQUIRE( mylib::magic_function(2, 6) == 14 );
    }
}