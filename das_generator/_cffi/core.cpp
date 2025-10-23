/*
Program     : Signal Generator using Time-Varying Room Impulse Responses

Description : Computes the response of an acoustic source to one or more
              microphones in a reverberant room using the image source 
              method [1,2].

              [1] J.B. Allen and D.A. Berkley,
              Image method for efficiently simulating small-room acoustics,
              Journal Acoustic Society of America, 65(4), April 1979, p 943.

              [2] P.M. Peterson,
              Simulating the response of multiple microphones to a single
              acoustic source in a reverberant room, Journal Acoustic
              Society of America, 80(5), November 1986.

Author      : E.A.P. Habets (e.habets@ieee.org)

MIT License

Copyright (C) 2024 E.A.P. Habets

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

#define _USE_MATH_DEFINES

#include <stdio.h>
#include <stdlib.h>
#include "math.h"
#include "core.h"

#define ROUND(x) ((x)>=0?(long)((x)+0.5):(long)((x)-0.5))

#ifndef M_PI
    #define M_PI 3.14159265358979323846
#endif

struct hpf_t {
    double  W;
    double  R1;
    double  B1;
    double  B2;
    double  A1;
} hpf;

// Modulus operation
int mod(int a, int b) {
    int ret = a % b;
    if(ret < 0)
        ret+=b;
    return ret;
}

double sinc(double x)
{
    if (x == 0)
        return(1.);
    else
        return(sin(x)/x);
}

// Check if the source position is constant
bool IsSrcPosConst(const double* sp_path, long nSourceSignal, long sample_idx, int offset) {
    bool bResult;
    
    bResult = (sp_path[sample_idx-offset]==sp_path[sample_idx-offset-1] &&
            sp_path[sample_idx-offset + nSourceSignal]==sp_path[(sample_idx-offset-1) + nSourceSignal] &&
            sp_path[sample_idx-offset + 2*nSourceSignal]==sp_path[(sample_idx-offset-1) + 2*nSourceSignal]);
    
    return(bResult);
}

// Check if the receiver position is constant
bool IsRcvPosConst(const double* rp_path, long nSourceSignal, long sample_idx, int mic_idx) {
    bool bResult;
    
    bResult = (rp_path[sample_idx + 3*mic_idx*nSourceSignal]==rp_path[(sample_idx-1) + 3*mic_idx*nSourceSignal] &&
            rp_path[sample_idx + nSourceSignal + 3*mic_idx*nSourceSignal]==rp_path[(sample_idx-1) + nSourceSignal + 3*mic_idx*nSourceSignal] &&
            rp_path[sample_idx + 2*nSourceSignal + 3*mic_idx*nSourceSignal]==rp_path[(sample_idx-1) + 2*nSourceSignal + 3*mic_idx*nSourceSignal]);
    
    return(bResult);
}

// Copy impulse response on row_idx-1 to row_idx
void copy_previous_rir(double* imp, int row_idx, int nRIR) {
    if (row_idx == 0) {
        for (int tmp_pos_idx = 0; tmp_pos_idx < nRIR; tmp_pos_idx++)
            imp[nRIR*tmp_pos_idx] = imp[(nRIR-1) + nRIR*tmp_pos_idx];
    }
    else {
        for (int tmp_pos_idx = 0; tmp_pos_idx < nRIR; tmp_pos_idx++)
            imp[row_idx + nRIR*tmp_pos_idx] = imp[(row_idx-1) + nRIR*tmp_pos_idx];
    }
}

// High-pass filter the impulse response
void hpf_imp(double* imp, int row_idx, int nRIR, hpf_t hpf) {
    double* Y = new double[3];
    double X0;
    
    for (int idx = 0; idx < 3; idx++) {
        Y[idx] = 0;
    }
    for (int idx = 0; idx < nRIR; idx++) {
        X0 = imp[row_idx + nRIR*idx];
        Y[2] = Y[1];
        Y[1] = Y[0];
        Y[0] = hpf.B1*Y[1] + hpf.B2*Y[2] + X0;
        imp[row_idx + nRIR*idx] = Y[0] + hpf.A1*Y[1] + hpf.R1*Y[2];
    }
    
    delete[] Y;
}

double sim_microphone(double x, double y, double z, double* microphone_angle, char mtype)
{
    if (mtype=='b' || mtype=='c' || mtype=='s' || mtype=='h')
    {
        double gain, vartheta, varphi, rho;

        // Polar Pattern         rho
        // ---------------------------
        // Bidirectional         0
        // Hypercardioid         0.25
        // Cardioid              0.5
        // Subcardioid           0.75
        // Omnidirectional       1

        // printf("[CORE] Microphone type: %c\n", mtype);

        switch(mtype)
        {
        case 'b':
            rho = 0;
            break;
        case 'h':
            rho = 0.25;
            break;
        case 'c':
            rho = 0.5;
            break;
        case 's':
            rho = 0.75;
            break;
        default:
            rho = 1;
        };

        vartheta = acos(z/sqrt(pow(x,2)+pow(y,2)+pow(z,2)));
        varphi = atan2(y,x);

        gain = sin(M_PI/2-microphone_angle[1]) * sin(vartheta) * cos(microphone_angle[0]-varphi) + cos(M_PI/2-microphone_angle[1]) * cos(vartheta);
        gain = rho + (1-rho) * gain;

        return gain;
    }
    else
    {
        return 1;
    }
}

void computeSignal(double* receiver_signals, double* source_signal, long nSourceSignal, double c, double fs, double* rp_path, int nMicrophones, int nRIR, double* sp_path, double* LL, double* beta, char* microphone_types, int nOrder, double* microphone_angles, int isHighPassFilter){

    // Define high-pass filter
    hpf.W = 2*M_PI*100/fs;
    hpf.R1 = exp(-hpf.W);
    hpf.B1 = 2*hpf.R1*cos(hpf.W);
    hpf.B2 = -hpf.R1 * hpf.R1;
    hpf.A1 = -(1+hpf.R1);
    
    // Declarations for image source method
    double*	     imp = new double[nRIR*nRIR];
    const double cTs = c/fs;
    const int    Tw = 2 * ROUND(0.004*fs);
    double*      LPI = new double[Tw+1];
    double*      hanning_window = new double[Tw+1];
    double*      r = new double[3];
    double*      s = new double[3];
    double*      L = new double[3];
    int*         n = new int[3];
    double*      angle = new double[2];

    // Initialization
    for (int idx = 0; idx < 3; idx++)
        L[idx] = LL[idx]/cTs;
    
    for (int idx = 0; idx < 3; idx++)
        n[idx] = (int) ceil(nRIR/(2*L[idx]));
    
    for (int idx = 0; idx < Tw+1; idx++)
        hanning_window[idx] = 0.5 * (1 + cos(2*M_PI*(idx+Tw/2)/Tw)); // Hanning window
    
    // Process each receiver seperately
    for (int mic_idx = 0; mic_idx < nMicrophones; mic_idx++) {
        angle[0] = microphone_angles[mic_idx];
        angle[1] = microphone_angles[mic_idx + nMicrophones];
        
        // Clear response matrix
        for (long counter = 0; counter < nRIR*nRIR; counter++)
            imp[counter] = 0;
        
        for (long sample_idx = 0; sample_idx < nSourceSignal; sample_idx++) {
            int	 row_idx_1;
            int	 row_idx_2;
            int  no_rows_to_update;
            bool bRcvInvariant_1;
            bool bSrcInvariant_1;
            bool bSrcInvariant_2;
            
            // if (sample_idx % 1024 == 0) {
            //    char buffer[50]; // Define a buffer to store the formatted string
            //    float progress = (float) (((mic_idx * nSourceSignal) + sample_idx + 1) / ((float) nMicrophones * nSourceSignal));
            //    printf(buffer, "%f%%\n", progress); // Format the float value into the buffer
            // }

            // Determine row_idx_1;
            row_idx_1 = sample_idx % nRIR;
            
            for(int idx=0; idx<3; idx++)
                r[idx] = rp_path[sample_idx + idx*nSourceSignal + 3*mic_idx*nSourceSignal]/cTs;
            
            if (sample_idx > 0) {
                bSrcInvariant_1 = IsSrcPosConst(sp_path, nSourceSignal, sample_idx, 0);
                bRcvInvariant_1 = IsRcvPosConst(rp_path, nSourceSignal, sample_idx, mic_idx);
            }
            else {
                bSrcInvariant_1 = false;
                bRcvInvariant_1 = false;
            }
            
            if ((bRcvInvariant_1 && bSrcInvariant_1) == false) {
                if (bRcvInvariant_1 == false && sample_idx > 0) {
                    if (sample_idx < nRIR)
                        no_rows_to_update = sample_idx;
                    else
                        no_rows_to_update = nRIR;
                }
                else {
                    no_rows_to_update = 1;
                }
                
                // Update response matrix
                for (int row_counter = 0; row_counter < no_rows_to_update; row_counter++) {
                    
                    row_idx_2 = mod(row_idx_1-row_counter, nRIR);
                    
                    if (row_counter > 0)
                        bSrcInvariant_2 = IsSrcPosConst(sp_path, nSourceSignal, sample_idx, row_counter);
                    else
                        bSrcInvariant_2 = false;
                    
                    if (bSrcInvariant_2 == false) {
                        double hu[6];
                        double refl[3];
                        int    q, j, k;
                        int    mx, my, mz;
                        
                        // Get source position
                        for(int idx=0;idx<3;idx++)
                            s[idx] = sp_path[sample_idx - row_counter + idx*nSourceSignal]/cTs;
                        
                        // Clear old impulse response
                        for (int idx = 0; idx < nRIR; idx++)
                            imp[row_idx_2 + nRIR*idx] = 0;
                        
                        // Compute new impulse response
                        for (mx = -n[0]; mx <= n[0]; mx++) {
                            hu[0] = 2*mx*L[0];
                            
                            for (my = -n[1]; my <= n[1]; my++) {
                                hu[1] = 2*my*L[1];
                                
                                for (mz = -n[2]; mz <= n[2]; mz++) {
                                    hu[2] = 2*mz*L[2];
                                    
                                    for (q = 0; q <= 1; q++) {
                                        hu[3] = (1-2*q)*s[0] - r[0] + hu[0];
                                        refl[0] = pow(beta[0], abs(mx-q)) * pow(beta[1], abs(mx));
                                        
                                        for (j = 0; j <= 1; j++) {
                                            hu[4] = (1-2*j)*s[1] - r[1] + hu[1];
                                            refl[1] = pow(beta[2], abs(my-j)) * pow(beta[3], abs(my));
                                            
                                            for (k = 0; k <= 1; k++) {
                                                hu[5] = (1-2*k)*s[2] - r[2] + hu[2];
                                                refl[2] = pow(beta[4], abs(mz-k)) * pow(beta[5], abs(mz));
                                                
                                                if (abs(2*mx-q)+abs(2*my-j)+abs(2*mz-k) <= nOrder || nOrder == -1) {
                                                    double dist = sqrt(pow(hu[3], 2) + pow(hu[4], 2) + pow(hu[5], 2));
                                                    int fdist = (int) floor(dist);
                                                    if (fdist < nRIR) {
                                                        for (int idx = 0; idx < Tw+1; idx++){
                                                            const double Fc = 1;
                                                            LPI[idx] = hanning_window[idx] * Fc * sinc(M_PI*Fc*(idx-(dist-fdist)-(Tw/2)));
                                                        }
                                                        
                                                        for (int idx = 0; idx < Tw+1; idx++) {
                                                            int pos = fdist-(Tw/2);
                                                            if (pos+idx >= 0 && pos+idx < nRIR) {
                                                                double strength = sim_microphone(hu[3], hu[4], hu[5], angle, microphone_types[mic_idx])
                                                                * refl[0]*refl[1]*refl[2]/(4*M_PI*dist*cTs);
                                                                imp[row_idx_2 + nRIR*(pos+idx)] += strength * LPI[idx];
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Apply original high-pass filter as proposed by Allen and Berkley
                        if (isHighPassFilter == 1) {
                            hpf_imp(imp, row_idx_2, nRIR, hpf);
                        }
                    }
                    else {
                        copy_previous_rir(imp, row_idx_2, nRIR);
                    }
                }
            }
            else {
                copy_previous_rir(imp, row_idx_1, nRIR);
            }
            
            // Calculate new output sample            
            for (int conv_idx = 0; conv_idx < nRIR; conv_idx++) {
                if (sample_idx-conv_idx >= 0) {
                    int tmp_imp_idx = mod(row_idx_1-conv_idx,nRIR);
                    receiver_signals[mic_idx + nMicrophones*sample_idx] += imp[tmp_imp_idx + nRIR*conv_idx] * source_signal[sample_idx - conv_idx];
                }
            }
        }
    }

    delete[] imp;
    delete[] LPI;
}
