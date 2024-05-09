from time import time
import asyncio

import numpy as np

from pydatacq import LiveData


class LiveFMSine(LiveData):
    '''
    An example class to demonstrate the LiveData class.
    It produces a FM modulated sinewave in the interval [-4𝛑:4𝛑],
    with modulation frequency of 3Hz and frequency
    deviation of 0.25Hz

    Values have been choosen to demonstrate update speed
    of the LiveWindow class as well, although this LiveFMSine
    class can be used in other consumers as well.
    '''

    def __init__(self,consumer_cb,fps):
        super().__init__(consumer_cb,fps=fps,yields=False)
        self.t = np.linspace(-2,2,1000)
        self.t0 = time() # starting time
        self.fc = 1 # carrier frequency
        self.f_mod = 3 # modulation frequency
        self.f_dev = self.fc / 4 # frequency deviation


    async def get_data(self):
        '''
        Produce the FM modulated sine wave.
        This function does not yield, it is a
        blocking function.
        '''
        now = time() - self.t0
        xm = np.sin(2 * np.pi * now * self.f_mod) # baseband signal
        y = np.sin(2 * np.pi * (self.fc + self.f_dev * xm) * self.t)
        return self.t * 2 * np.pi,y