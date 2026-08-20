#include <pybind11/pybind11.h>

PYBIND11_MODULE(smoke_native, m) {
    m.def("add", [](int a, int b) {
        return a + b;
    });
}
