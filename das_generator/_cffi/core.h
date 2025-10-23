#ifndef DAS_GENERATOR_CFFI_CORE_H
#define DAS_GENERATOR_CFFI_CORE_H

#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

void computeSignal(double* receiver_signals, double* source_signal, long nSourceSignal, double c, double fs, double* rp_path, int nMicrophones, int nRIR, double* sp_path, double* LL, double* beta, char* microphone_types, int nOrder, double* microphone_angles, int isHighPassFilter);

#ifdef __cplusplus
}
#endif

#endif
