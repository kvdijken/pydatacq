import argparse
import builtins
import asyncio

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import quantiphy as q

from sds import SDS
import fft_calculations
from fft_calculations import fft
from live_sds import LiveSDS
from live_window import LiveWindow
import matplotlib_rc

live_sds = None

parser = argparse.ArgumentParser(description='Display FFT for a channel on Siglent oscilloscope.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-C',dest='channel',required=True,type=int,help='channel to display',choices=[1,2])
parser.add_argument('-a','--average',type=int,default=1,help='Averaging')
parser.add_argument('-H','--maxhold',action='store_true',default=False,help='Max hold')
parser.add_argument('-c','--centre',required=True,help='Centre frequency (Hz)')
parser.add_argument('-s','--span',required=True,help='Span (Hz)')
parser.add_argument('-m','--min',type=int,default=-120,help='Min power (dBvrms)')
parser.add_argument('-M','--max',type=int,default=-40,help='Max power (dBvrms)')
parser.add_argument('-ip',required=True,help='ip address of the oscilloscope')
parser.add_argument('-port',default=5025,type=int,help='port on which the oscilloscope is listening')
parser.add_argument('-t','--title',metavar='NAME',help='plot title')
parser.add_argument('-w','--window',metavar='NAME',help='window title')
parser.add_argument('-fps',action='store_true',help='show waveform updates per second')
parser.add_argument('-tc','--triggercoupling',type=int,choices=[0,1],default=1,
                    help='1 = set channel coupling to AC and set trigger source to fft channel, trigger type to edge triggering, trigger level to 50%%, trigger hold to off and trigger mode to auto, 0 = do not set')

args = parser.parse_args()

print()
print('fft.py was called with the following arguments:')
print(' '.join(f'{k}={v}' for k, v in vars(args).items()))
print('')

# channel to sample
channel = args.channel-1

# centre frequency
centre = q.Quantity(args.centre).real

# span
span = q.Quantity(args.span).real

min = args.min
max = args.max

# title of the plot
plotTitle = args.title

# window title
windowTitle = args.window

# ip address of oscilloscope
ip = args.ip
                    
# port on which the oscilloscope will listen
port = args.port

# fps
fps = args.fps

# averaging
avg = args.average

# max hold
maxhold = args.maxhold

# triggercoupling
triggercoupling = (args.triggercoupling == 1)



yf_avg = None
yf_max = None
# 
line = None
_fft_max_f = None

#
async def processWave(wave):
    global yf_avg, yf_max, line, _fft_max_f
    c = wave[0]

    # get the fft
    t = wave[1][0]
    v = wave[1][1]
    t,v,fft_max_f,fft_f_resolution  = fft_calculations.fft((t,v))

    # select frequencies of interest
    fft = fft_calculations.frequency_window((t,v),centre,span)
    xf = fft[0]
    yf = fft[1]

    # What acquisition mode (normal, average or max hold)?
    # also take into account is the data length has changed.
    # If so, reset all average and max values.
    if avg > 1:
        # averaging
        if yf_avg is None:
            yf_avg = yf
        else:
            if yf_avg.ndim == 1:
                len_avg = yf_avg.shape[0]
            else:
                len_avg = yf_avg.shape[1]
            if len(yf) != len_avg:
                # reset
                yf_avg = yf
            else:
                yf_avg = np.vstack((yf_avg,yf))
                if yf_avg.shape[0] > avg:
                    yf_avg = np.delete(yf_avg,(0),axis=0)
        if yf_avg.ndim > 1:
            yf = np.mean(yf_avg,axis=0)
    elif maxhold:
        # maxhold
        if yf_max is None:
            yf_max = yf
        elif len(yf) != len(yf_max):
            # reset
            yf_max = yf
        else:
            yf_max = np.maximum(yf_max,yf)
            yf = yf_max

    if line is None or True:
        line = live_window.ax.plot(xf,yf,animated=True)[0]
    else:
        line.set_data(xf,yf)

    if _fft_max_f is None or (_fft_max_f != fft_max_f):
        if (len(xf) == 0) or (fft_max_f < centre+span/2):
            c = 'red'
        else:
            c = 'black'
        plt.title(r'$f_{max}=%s$' % (q.Quantity(fft_max_f,"Hz"),),loc='right',color=c)
        plt.title(r'$\Delta f=%s$' % (q.Quantity(fft_f_resolution,"Hz"),),loc='left',color='black')
        live_window.redraw()
        _fft_max_f = fft_max_f

    await live_window.draw(line)


# 
def XAxis_Formatter(x,pos):
    return q.Quantity(x,'Hz').render(form='si')


def setTriggerCoupling():
    '''
    Having the trigger controls on the oscilloscope
    leads to bad performance for the fft. This method
    sets all trigger settings to the right value fo rgood performance.

    Set trigger settings to:
    - source = channel from which the fft is taken.
    - type = edge triggering
    - level = 50%
    - hold type = none
    - triggertype = auto

    Set the channel coupling to AC coupling.
    '''
    sds = SDS(ip,port)
    sds.send(f'C{channel+1}:TRCP AC')
    sds.send('TRIG_MODE AUTO')
    sds.send(f'TRSE EDGE,SR,C{channel+1},HT,OFF')
    sds.send('SET50')


def onclose(event):
    exit()


# 
live_sds = LiveSDS(f'FFT from channel {channel+1} SDS1202X-E',
                   ip,port,channel,processWave,fps)
if windowTitle is None:
    windowTitle = f'FFT Channel {int(channel+1)}'
live_window = LiveWindow(windowTitle,plotTitle,onclose_cb=onclose)

if triggercoupling:
    setTriggerCoupling()

# Customize the window for FFT output
live_window.ax.xaxis.set_major_formatter(XAxis_Formatter)
plt.xlabel('frequency')
plt.ylabel(r'Signal strength   ($dB_{V_{rms}}$)')
plt.ylim(min,max)
plt.xlim(builtins.max(centre-span/2,0),centre+span/2)
plt.autoscale(enable=False)

# Start acquisition
live_sds.start()