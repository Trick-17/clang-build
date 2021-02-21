#include <iostream>

#include <libA.hpp>
#include <libC.hpp>

int main() {
  std::cerr << "Hello! libC::half(libA::triple(4)) returned "
            << libC::half(libA::triple(4)) << std::endl;
  return 0;
}