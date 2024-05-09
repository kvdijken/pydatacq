import matplotlib.pyplot as plt
import numpy as np

from live_fm_sine import LiveFMSine
from live_window import LiveWindow

plt.rcParams['toolbar'] = 'None'


# 
async def process(data):
    '''
    This function prepares the plot of the data
    and lets it draw by live_window.
    '''
    line = live_window.ax.plot(data[0],data[1],color='k',animated=True)[0]
    await live_window.draw(line)


# 
def onclose(event):
    exit()


# 
live_fm_sine = LiveFMSine(process,fps=True)
live_window = LiveWindow(windowTitle='Frequency Modulated sine',onclose_cb=onclose)

# set the ticks and ticklabels
live_window.ax.set_xticks([-4*np.pi,-3*np.pi,-2*np.pi,-np.pi,0,np.pi,2*np.pi,3*np.pi,4*np.pi],
                          ['$-4\pi$','$-3\pi$','$-2\pi$','$-\pi$','0','$\pi$','$2\pi$','$3\pi$','$4\pi$'])

plt.ylim(-1.5,1.5)
plt.xlim(-4*np.pi,4*np.pi)
live_fm_sine.start()
