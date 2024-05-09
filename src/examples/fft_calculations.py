import asyncio
import numpy as np
from scipy.fft import rfft, rfftfreq
from scipy.signal.windows import flattop


# x in V
sq2 = np.sqrt(2)
def V_to_Vrms(x):
    return x / sq2


# x in Vrms
def Vrms_to_dBVrms(x):
    return 20*np.log10(x)


# x in V
def V_to_dBV(x):
    return 20*np.log10(x)



def frequency_window(fft,centre,span):
    '''
    Creates a frequency window on FFT results 'fft'.

    Parameters:

    fft : (f,y), fft results, where f is an array of frequency bins, and 
          y is an equally sized array of magnitudes.
    centre : centre of the frequency window
    span : span of the frequency window.

    Returns:

    (f',y'), where f' = an array with frequency bins ranging from centre-span/2
             to centre+span/2, and y' the accompanying magnitudes.
    '''
    xf = fft[0]
    yf = fft[1]
    min = centre - span / 2
    if min < 0:
        min = 0
    max = centre + span / 2
    i = np.nonzero(xf<=min)[0][-1]
    j = np.nonzero(xf<=max)[0][-1]
    return (xf[i:j],yf[i:j])


# returns f, v (dB)
# channel = 0 | 1
# output = 'dBVrms' | 'dBV' | 'V'
def fft(wave, max_f=None, output='dBVrms'):
    '''
    Calculates the Fast Fourier Transform of a waveform obtained from the oscilloscope.
    No error checking whatsoever is done.

    Parameters:

    channel : the channel to obtain the waveform for, either 0 (for channel 1)
                or 1 (for channel 2).
    max_f : maximum frequency (in Hz) of the specturm to return. 
            If None, the complete spectrum will be returned.
    output : Determines in what format the result yf of the fft will be returned.
                'dBVrms' = output yf in dBVrms
                'dBV' = output yf in dBV
                'V' = output yf in V

    Returns:

    xf : frequency bins [0..max_f]
    yf : magnitude bins [0..max_f]
    fft_max_f : maximum frequency in fft
    fft_f_res : frequency resolution (in Hz)
    '''

    y = wave[1]
    Tmax = wave[0][-1] + wave[0][1]
    if y is None:
        return
    if Tmax is None:
        return
    
    N = y.size

    fft_f_res = 1 / Tmax
    sara = N / Tmax
    fft_max_f = sara / 2

    # samplerate (samples/second)
    samplerate = N / Tmax
    samplespacing = 1/samplerate
    xf = rfftfreq(N,samplespacing)

    # perform fft, returns yf in V
    yf = 2*np.abs(rfft(y,norm='forward'))

    if output == 'dBVrms':
        yf = Vrms_to_dBVrms(V_to_Vrms(yf))
    elif output == 'dBV':
        yf = V_to_dBV(yf)

    # Return results up to the highest frequency of interest.
    if max_f is None:
        i = len(xf) - 1
    else:
        # Find the index of the highest frequency of interest
        # This highest frequency of interest will be included
        # in the returned results.
        i = np.nonzero(xf<=max_f)[0][-1]
        if xf[i] < max_f:
            # max_f is not included in xf[:i+1], include it, if possible.
            i = i + 1
            if i >= len(xf):
                # prevent index out of range error
                i = len(xf) - 1

    return xf[:i+1], yf[:i+1], fft_max_f, fft_f_res


def peakbin(yf,bin) -> int:
    m = bin
    # search up
    i = bin + 1
    while (i < len(yf)) and (yf[i] >= yf[m]):
        m = i
        i = i + 1
    # search down
    i = bin-1
    while (i>=0) and (yf[i] >= yf[m]):
        m = i
        i = i - 1
    return m


# _bin is a synonym for _getnearpos
# _getnearpos finds the closest value in an array
def _bin(array,value):
    idx = (np.abs(array-value)).argmin()
    return idx


# returns (thd,xf,yf,bins)
# note that the returned yf is not in dB
# thd in %
# bins: indices in xf for harmonics
#
# channel = 0 | 1
def thd(fft,f0,correct_peaks=False,min_level=None):
    """
    Calculates THD (total harmonic distortion, in %) of a waveform
    obtained from the oscilloscope.

    No error checking whatsoever is done.

    Parameters:

    fft : (xf,yf) xf = frequency bins, yf = voltage
    correct_peaks : If correct_peaks == True will correct harmonics bins if
                    directly neighbouring bins have higher signal level (default=False).
    min_level : minimum signal level (in dBV) for harmonics to be included in the
                THD calculation (default=None). If min_level == None all harmonics bins
                will be included, also if the signal appears to be below the noise level.

    Returns:

    thd : total harmonic distortion (in %)
    bins : array of harmonics bins (index into xf and yf).
    """

    xf = fft[0]
    yf = fft[1]

    # Create list of harmonic frequencies within [f0:xf[-1]]
    freqs = np.arange(f0,xf[-1]+1,f0)

    # Get the bins for all harmonics
    bins = [_bin(xf,f) for f in freqs]

    if correct_peaks:
        # correct bins for the exact location of the nearby peak
        bins = [peakbin(yf,p) for p in bins]

    if min_level is not None:
        min = 10**(min_level/20) # from dBV to V
        # only take into regard bins for for yf>min
        # always include the fundamental
        bins = [bin for i, bin in enumerate(bins) if i==0 or yf[bin]>min]

    # Calculate THD in %
    vsq = [yf[p]**2 for p in bins[1:]]
    vsq_sum = sum(vsq)
    thd = 100 * np.sqrt(vsq_sum) / yf[bins[0]]

    return thd,bins

