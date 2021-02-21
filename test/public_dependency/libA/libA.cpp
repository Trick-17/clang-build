#include <libA.hpp>
#include <libB.hpp>

namespace libA {

float triple(float x) { return libB::triple(x); }

} // namespace libA