import argparse
import asyncio

import numpy as np
import matplotlib.pyplot as plt
import quantiphy as q

from sds import SDS
from fft_calculations import V_to_Vrms, Vrms_to_dBVrms, fft, thd
from live_sds import LiveSDS
from live_window import LiveWindow
import matplotlib_rc

parser = argparse.ArgumentParser(description='Display FFT and calculate THD for a channel on Siglent SDS1202X-E oscilloscope.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-C',dest='channel',required=True,type=int,help='channel to display',choices=[1,2])
parser.add_argument('-f0',default='1k',metavar='FREQ',help='fundamental frequency (in Hz)')
parser.add_argument('-max_f',default='25k',metavar='FREQ',help='maximum frequency to display / use for calculations (in Hz)')
parser.add_argument('-f','--floor',default=-85,type=int,help='minimum level of harmonics (in dBvrms)')
parser.add_argument('-ip',required=True,help='ip address of the oscilloscope')
parser.add_argument('-port',default=5025,type=int,help='port on which the oscilloscope is listening')
parser.add_argument('-t','--title',metavar='NAME',help='plot title')
parser.add_argument('-w','--window',metavar='NAME',help='window title')
parser.add_argument('-fps',action='store_true',help='show waveform updates per second')

args = parser.parse_args()

print('thd.py was called with the following arguments:')
print(' '.join(f'{k}={v}' for k, v in vars(args).items()))
print('')

# channel to sample
channel = args.channel-1

# fundamental frequency from which to calculate the THD
f0 = q.Quantity(args.f0).real

# Max frequency of interest
max_f = q.Quantity(args.max_f).real

# minimum level for harmonics
floor = args.floor

# title of the plot
plotTitle = args.title

# window title
windowTitle = args.window

# ip address of oscilloscope
ip = args.ip
                    
# port on which the oscilloscope will listen
port = args.port

# whether to display fps
fps = args.fps


# 
async def plot(fft,thd,bins):
    items = []

    xf = fft[0]
    yf = fft[1] # yf in V

    # transform to dBvrms for the display
    yf_dB = Vrms_to_dBVrms(V_to_Vrms(yf))
    s0 = yf_dB[bins[0]]
    if len(bins) > 1:
        s1 = yf_dB[bins[1]]
        textstr = '\n'.join((r'$THD=%.2f$' % (thd, ) + '%',
                            r'$s_0=%i dB_{V_{rms}}$' % (s0,),
                            r'$s_1=%i dB_c$' % (int(s1-s0),),
                            ))
    else:
        textstr = '\n'.join((r'$THD=%.2f$' % (thd, ) + '%',
                            r'$s_0=%i dB_{V_{rms}}$' % (s0,),
                            ))

    props = dict(boxstyle='round', facecolor='lightgrey', alpha=0.75)

    # place a text box in upper left in axes coords
    item = live_window.ax.text(0.65, 0.95, textstr, transform=live_window.ax.transAxes, fontsize=14,
            verticalalignment='top', bbox=props,animated=True)
    items.append(item)

    # plot a x at harmonics, and remember the x's to remove them later
    for p in bins[1:]:
        item = live_window.ax.scatter(xf[p],yf_dB[p],marker=7,color='blue',animated=True)
        items.append(item)

    # plot a dot at fundamental frequency, and remember the dot to remove it later
    item = live_window.ax.scatter(xf[bins[0]],yf_dB[bins[0]],marker=7,color='red',animated=True)
    items.append(item)

    # plot fft
    item = live_window.ax.plot(xf,yf_dB,animated=True)[0]
    items.append(item)

    await live_window.draw(items)


async def processWave(wave):
    t = wave[1][0]
    v = wave[1][1]
    _fft = fft((t,v), max_f=max_f, output='V')
    _thd, bins = thd(_fft, f0, min_level=floor, correct_peaks=False)
    await plot(_fft, _thd, bins)


# 
def XAxis_Formatter(x,pos):
    return q.Quantity(x,'Hz').render(form='si')


# 
def onclose(event):
    exit()


# 
live_sds = LiveSDS(f'THD from channel {channel+1} SDS1202X-E',ip,port,channel,processWave,fps)
if windowTitle is None:
    windowTitle = f'FFT Channel {int(channel+1)}'
live_window = LiveWindow(windowTitle,plotTitle,onclose_cb=onclose)

# Customize the window for FFT output
live_window.ax.xaxis.set_major_formatter(XAxis_Formatter)
plt.xlabel('frequency')
plt.ylabel(r'Signal strength   $dB_{V_{rms}}$')
plt.ylim(-120,40)

# Start acquisition
live_sds.start()