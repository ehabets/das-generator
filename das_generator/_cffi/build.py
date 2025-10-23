import sys
from cffi import FFI

das_generator = FFI()

compile_extras = {
    "libraries": ["m"],
}

# MSVC does not like -march=native -lm
if sys.platform == "win32":
    compile_extras = {}

das_generator.set_source(
    "das_generator._bindings",
    '#include "core.h"',
    sources=["das_generator/_cffi/core.cpp"],
    include_dirs=["das_generator/_cffi"],
    **compile_extras
)

das_generator.cdef(
    """
void computeSignal(
    double* receiver_signals,
    double* source_signal,
    long nSourceSignal,
    double c,
    double fs,
    double* rp_path,
    int nMicrophones,
    int nRIR,
    double* sp_path,
    double* LL,
    double* beta,
    char* microphone_types,
    int nOrder,
    double* microphone_angles,
    int isHighPassFilter
);
"""
)

if __name__ == "__main__":
    das_generator.compile()
