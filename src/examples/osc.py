import asyncio
import argparse
import uvloop

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import quantiphy as q

from sds import SDS
import fft_calculations
from fft_calculations import V_to_Vrms, Vrms_to_dBVrms, fft, thd
from live_sds import LiveSDS
from live_window import LiveWindow
import matplotlib_rc

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

live_sds = None


dpi = 102 #decided by display device

default_text_size_points = 10
default_line_width_points = 1

# matplotlib rules
mpl_points_per_inch = 72
mpl_pixels_per_point = dpi / mpl_points_per_inch

line_width_pixels = 1
line_width_points = line_width_pixels / mpl_pixels_per_point
plt.rcParams['lines.linewidth'] = line_width_points
_lw = line_width_points

text_size_points = default_text_size_points
plt.rcParams['font.size'] = text_size_points

plt.rcParams['figure.dpi'] = dpi


parser = argparse.ArgumentParser(description='Displays waveform for one or more channels on Siglent SDS1202X-E oscilloscope.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-C',dest='channels',required=True,help='channels to display')
parser.add_argument('-ip',required=True,help='ip address of the oscilloscope')
parser.add_argument('-port',default=5025,type=int,help='port on which the oscilloscope is listening')
parser.add_argument('-t','--title',metavar='NAME',help='plot title')
parser.add_argument('-w','--window',metavar='NAME',help='window title')
parser.add_argument('-fps',action='store_true',help='show waveform updates per second')


args = parser.parse_args()

print()
print('osc.py was called with the following arguments:')
print(' '.join(f'{k}={v}' for k, v in vars(args).items()))
print('')


def decode_channels(arg):
    c = set()
    if '1' in arg:
        c = {0}
    if '2' in arg:
        c.add(1)
    return c


# channel to sample
channels = decode_channels(args.channels)

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

live_sds = None
items = {0:[],1:[]}
persistence = 1
_alpha = 1 / persistence


# 
async def _processWave(wave):
    c = wave[0]
    t = wave[1][0]
    v = wave[1][1]
    if c == 0:
        # channel 1
        color = 'yellow'
    else:
        # channel 2
        color = 'fuchsia'

    item = live_window.ax.plot(t,v,color=color,zorder=1-c,alpha=_alpha,lw=_lw)[0]
    items[c].append(item)
    while len(items[c])>persistence:
        items[c].pop(0).remove()
    return True


#
line = [None,None]
tmax = None
async def processWave(wave):
    global line, tmax
    c = wave[0]
    t = wave[1][0]
    v = wave[1][1]
    if c == 0:
        # channel 1
        color = 'yellow'
    else:
        # channel 2
        color = 'fuchsia'

    if line[c] is None:
        line[c] = live_window.ax.plot(t,v,color=color,zorder=1-c,alpha=_alpha,lw=_lw)[0]
    else:
        # We set x and y data here because len(wave) may have changed.
        line[c].set_data(t,v)

    # x-axis ticks logic
    if tmax != t[-1]:
        # timebase has changed, redraw everything
        live_window.ax.set_xlim(t[0],t[-1])
        live_window.redraw()
    tmax = t[-1]

    await live_window.draw([line[c]])


# 
def XAxis_Formatter(x,pos):
    return q.Quantity(x,'s').render(form='si')


# 
def onclose(event):
    exit()


# 
live_sds = LiveSDS(f'Channels {channels} from SDS1202X-E',ip,port,channels,processWave,fps)
if windowTitle is None:
    windowTitle = f'Oscilloscope channel {",".join(str(c+1) for c in channels)}'
live_window = LiveWindow(windowTitle,plotTitle,onclose_cb=onclose)

# Customize the window for oscilloscope output
live_window.ax.xaxis.set_major_formatter(XAxis_Formatter)
live_window.ax.set_facecolor("black")
plt.xlabel('time')
plt.ylabel('signal   (V)')

# Start acquisition
live_sds.start()