import asyncio
import struct
import logging
from time import time, asctime

import numpy as np
from scipy.fft import rfft, rfftfreq
from scipy.signal.windows import flattop
import quantiphy as q

from siglent import Siglent


CH = ['C1','C2']

### Timebase lookup
tbase_lookup = np.array([200e-12,
                500e-12,
                1e-9,
                2e-9,
                5e-9,
                10e-9,
                20e-9,
                50e-9,
                100e-9,
                200e-9,
                500e-9,
                1e-6,
                2e-6,
                5e-6,
                10e-6,
                20e-6,
                50e-6,
                100e-6,
                200e-6,
                500e-6,
                1e-3,
                2e-3,
                5e-3,
                10e-3,
                20e-3,
                50e-3,
                100e-3,
                200e-3,
                500e-3,
                1,
                2,
                5,
                10,
                20,
                50,
                100])
_tbase_lookup = ['200PS',
                '500PS',
                '1NS',
                '2NS',
                '5NS',
                '10NS',
                '20NS',
                '50NS',
                '100NS',
                '200NS',
                '500NS',
                '1US',
                '2US',
                '5US',
                '10US',
                '20US',
                '50US',
                '100US',
                '200US',
                '500US',
                '1MS',
                '2MS',
                '5MS',
                '10MS',
                '20MS',
                '50MS',
                '100MS',
                '200MS',
                '500MS',
                '1S',
                '2S',
                '5S',
                '10S',
                '20S',
                '50S',
                '100S']


class SDS(Siglent):
    '''
    This provides a thin class of common SCPI commands for the SDS1000, SDS200X and 
    SDS200X-E series of osclloscopes from Siglent.

    This class has only been tested on the SDS1202X-E model.

    See the "SDS1000 Series & SDS2000X & SDS2000X-E ProgrammingGuide PG01-E02D.pdf"
    which can be downloaded from https://www.siglent.com/upload_file/document/SDS1000%20Series&SDS2000X&SDS2000X-E_ProgrammingGuide_PG01-E02D.pdf
    '''

    _divisions = 14
    _channel = 0

    # This translates the display value (-127..128) to a voltage.
    def _toV(self,x,vgain,voffset,probe_att):
        return (x / 128 * vgain * 5 - voffset) * probe_att


    #
    def _to_dBVrms(self,x):
        return 20*np.log10(x)


    async def async_query_rawwave(self,ch):
        '''
        Asynchronously request for a waveform from the oscilloscope.

        The protocol is described in:
        SDS1000 Series&SDS2000X&SDS2000X-E_ProgrammingGuide_PG01-E02D.pdf, page 264

        Parameters:

        ch : channel {0,1} to get the waveform from

        Returns:

        wave : bytes of the waveform
        '''
        reader, writer = await asyncio.open_connection(self.ip,self.port,limit=15_000_000)

        try:
            cmd = f'{CH[ch]}:WF? DAT2'
            b_cmd = bytes(cmd,'ascii')
            writer.write(b_cmd + b'\n')
            await writer.drain()

            # first read the header
            header = await reader.readexactly(22)

            # get the size of the data block
            size = int(header[13:22])
            wave = await reader.readexactly(size) # this does not include the thermination '\n'n' which is sent
            await reader.readexactly(2)
        finally:
            writer.close()
            await writer.wait_closed()

        return wave


    # Gets the wave for the channel
    # Returns (V,Tmax)
    
    _wavetime = None

    # This version follows the SDS manual and uses the official
    # queries, not the waveform descriptor for which the docs
    # cannot be found anymore.
    async def async_getwave(self, channel):
        # Many experiments have shown that that it doing these
        # four request concurrently does not pay off. It takes
        # more time to create tasks and schedule them than it
        # takes to run the four request sequentially.

        # timebase
        cmd = f'TIME_DIV?'
        response = await self.async_query(cmd)
        timebase = float(response[5:-2])

        T = timebase * self.divisions()
        wait = T * 4
        now = time()

        if True:
            if self._wavetime is not None:
                # decide how long ago it was the last waveform
                # was acquired. Wait more until it was 'wait'
                # seconds ago to let the oscilloscope acquire
                # a new waveform.
                passed = now - self._wavetime
                if passed < wait:
                    sleep = wait - passed
                    print(f'{asctime()}: sleep {sleep}')
                    await asyncio.sleep(sleep)
            self._wavetime = now

        # Get wave
        wave = await self.async_query_rawwave(channel)
        w = np.frombuffer(wave,dtype=np.int8)
        w = np.where(w>127, w-256, w)

        # Get VDIV
        cmd = f'{CH[channel]}:VDIV?'
        response = await self.async_query(cmd)
        vdiv = float(response[8:-2])

        # Get VOFFSET
        cmd = f'{CH[channel]}:OFFSET?'
        response = await self.async_query(cmd)
        offs = float(response[8:-2])

        v = w * vdiv / 25 - offs

        return v, timebase*self._divisions



    # Gets the wave for the channel
    # Returns (t,V)
    # channel = 0 | 1
    async def async_getwave_x(self, channel):
        '''
        Obtains the current waveform from the oscilloscope on the given channel.

        Parameters:

        channel : the channel for which to obtain the waveform from (0 or 1).

        Returns:
        t : numpy array with sample time, starting at 0 (in seconds)
        V : numpy array with voltage on time t (in V).
        '''
        y, Tmax = await self.async_getwave(channel)
        if y is None:
            return None
        t = np.linspace(0,Tmax,y.size,endpoint=False)
        return t, y


    # Sets the oscilloscopes timebase
    # tb is an index in tbase_lookup
    def setTimebase(self,tb):
        '''
        Set the osciloscope timebase.

        Parameters:

        tb : (int | str) If int, tb is index into tbase_lookup for the time / horizontal division.
             If str, tb must be one of the strings in _tbase_lookup

        Returns:

        None
        '''
        if type(tb) == int:
            # lookup and convert to str
            tb = _tbase_lookup[tb]
        cmd = f'TDIV {tb}'
        self.send(cmd)


    # Set the timebase to the first value larger than secs_per_div
    def setTimebaseAtLeast(self,secs_per_div):
        '''
        Set the oscilloscopes timebase to secs_per_div or the next 
        available larger timebase.

        Parameters:

        secs_per_div : minimal timebase per horizontal division (in seconds)

        Returns:

        None
        '''
        # Find first timebase in tbase_lookup which is larger than 'secs'
        tb = np.where(tbase_lookup > secs_per_div)[0][0]
        self.setTimebase(tb)


    # Returns the number of horizontal divisions
    def divisions(self):
        '''
        Returns the number of divisions for the oscilloscope.

        Parameters:

        None

        Returns:
        The number of divisions for the oscilloscope, 14.
        '''
        return self._divisions


    # Returns the settings for ch as a dictionary
    # 'att' = attenuation (1 | 10 | 100 | ...)
    # 'bw' = bandwidth limited (True | False)
    # 'cpl' = coupling
    # 'offs' = offset (V)
    # 'skew' = skew (s)
    # 'trace' = trace ('ON' | 'OFF')
    # 'unit' = unit ()
    # 'vdiv' = volts per division (V)
    # 'invert' = inverted (True | False)
    #
    # ch = 'C1' | 'C2'
    def channelSettings(self,ch):
        '''
        Returns the settings for a channel on the oscilloscope.
        This is not a very quick method to return.

        Parameters:

        ch : 'C1' or 'C2', channel to obtain the settings for.

        Returns:

        Settings for the channel ch as a dictionary.

        Keys:
        'att' = attenuation (1 | 10 | 100 | ...)
        'bw' = bandwidth limited (True | False)
        'cpl' = coupling ('AC' or 'DC' or 'GND')
        'offs' = offset (V)
        'skew' = skew (s)
        'trace' = trace ('ON' | 'OFF')
        'unit' = unit ('V' or 'A')
        'vdiv' = volts per division (V)
        'invert' = inverted (True | False)
        '''
        # attenuation
        cmd = f'{ch}:ATTENUATION?'
        response = self.query(cmd).decode('ascii')
        # Returns: 'C1:ATTN 10\n'
        att = int(response[8:-1])

        # bandwidth limit
        cmd = f'{ch}:BANDWIDTH_LIMIT?'
        response = self.query(cmd).decode('ascii')
        # Returns:
        # 'C1:BWL ON\n'
        # 'C1:BWL OFF\n'
        match response[7:-1]:
            case 'ON':
                bw = True
            case 'OFF':
                bw = False

        # coupling
        #<coupling>:={A1M,A50,D1M,D50,GND}
        #A — alternating current.
        #D — direct current.
        #1M — 1MΩ input impedance.
        #50 — 50Ω input impedance.
        cmd = f'{ch}:COUPLING?'
        response = self.query(cmd).decode('ascii')
        match response[7:-1]:
            case 'A1M':
                cpl = 'AC'
            case 'A50':
                cpl = 'AC'
            case 'D1M':
                cpl = 'DC'
            case 'D50':
                cpl = 'DC'
            case 'GND':
                cpl = 'GND'

        # offset
        cmd = f'{ch}:OFFSET?'
        response = self.query(cmd).decode('ascii')
        # Returns: 'C1:OFST 0.00E+00V\n'
        offs = float(response[8:-2])

        # skew
        cmd = f'{ch}:SKEW?'
        response = self.query(cmd).decode('ascii')
        # Returns: 'C1:SKEW 0.00E+00S\n'
        skew = float(response[8:-2])

        # trace
        cmd = f'{ch}:TRACE?'
        response = self.query(cmd).decode('ascii')
        # Returns:
        # 'C1:TRA ON\n'
        # 'C1:TRA OFF\n'
        trace =  response[7:-1]

        # unit
        cmd = f'{ch}:UNIT?'
        response = self.query(cmd).decode('ascii')
        # Returns:
        # 'C1:UNIT V\n'
        # 'C1:UNIT A\n'
        unit = response[8:-1]

        # Volts per division
        cmd = f'{ch}:VDIV?'
        response = self.query(cmd).decode('ascii')
        # Returns 'C1:VDIV 2.00E-01V\n'
        vdiv = float(response[8:-2])

        # inverted
        cmd = f'{ch}:INVS?'
        response = self.query(cmd).decode('ascii')
        # Returns:
        # 'C1:INVS ON\n'
        # 'C1:INVS OFF\n'
        match response[8:-1]:
            case 'ON':
                invert = True
            case 'OFF':
                invert = False

        return {'att':att, 
                'bw':bw, 
                'cpl':cpl, 
                'offs':offs, 
                'skew':skew, 
                'trace': trace, 
                'unit':unit,
                'vdiv':vdiv,
                'invert':invert}
    

    def timebaseSettings(self):
        '''
        Returns the timebase settings for the oscilloscope.

        Parameters:

        None

        Returns:

        Returns the horizontal timebase in seconds per division.
        '''

        cmd = f'TIME_DIV?'
        response = self.query(cmd).decode('ascii')

        # for a 10ms timebase "TDIV 1.00E-02S\n" is returned.
        return float(response[5:-2])
    

    def memorySettings(self):
        '''
        Returns the memory size setting for the oscilloscope.

        Parameters:

        None

        Returns:

        Returns the memory size as a string:
        'MSIZ 14K' = 14_000
        'MSIZ 140K' = 140_000
        'MSIZ 1.4M' = 1_400_000
        'MSIZ 14M' = 14_000_000
        '''

        cmd = 'MEMORY_SIZE?'
        response = self.query(cmd).decode('ascii')
        # returns:
        # 'MSIZ 14K\n'
        # 'MSIZ 140K\n'
        # 'MSIZ 1.4M\n'
        # 'MSIZ 14M\n'
        match response[5:-1]:
            case '14K':
                mem = 14_000
            case '140K':
                mem = 140_000
            case '1.4M':
                mem = 1_400_000
            case '14M':
                mem = 14_000_000
            case _:
                mem = None
        return mem


    def acquireSettings(self):
        '''
        Returns the acquisition settings for the oscilloscope.

        Parameters:

        None

        Returns:

        Returns a string representing the sampling method and a float 
        for the samplerate in samples per second.

        Sampling string:
        'SAMPLING' = normal
        'PEAK_DETECT' = peak detection
        'AVERAGE,16' = averaging, no details
        'HIGH_RES' = high resolution, no details
        '''

        cmd = 'ACQW?'
        response = self.query(cmd).decode('ascii')
        # returns:
        # 'ACQW SAMPLING\n'
        # 'ACQW PEAK_DETECT\n'
        # 'ACQW AVERAGE,16\n'
        # 'ACQW HIGH_RES\n'
        acq = response[5:-1]

#        cmd = 'AVERAGE_ACQUIRE?'
#        response = self.query(cmd).decode('ascii')
        # returns: 'AVGA 16\n'
#        avg = int(response[5:-1])

        # sample rate
        cmd = 'SARA?'
        # Returns: 'SARA 1.00E+09Sa/s\n'
        response = self.query(cmd).decode('ascii')
        sara = float(response[5:-5])

        # For now don't bother decoding this
        return acq, sara
    

    # Collect the settings from the SDS1202X-E
    # output:
    # 'tuple': returns settings as tuple
    # 'table': returns settings as a markdown table (use Ctrl-Shift-V to paste into Obsidian)
    # 'text': returns settings as printable text
    def settings(self,output='tuple'):
        '''
        Returns the settings (configuration) of the oscilloscope.
        The format to be returned can be given by the parameter output.
        Configuration details include channel settings (for both channels),
        timebase settings, memory size setting and acquisition settings.

        Parameters:

        output : determines the format of the result
                 'tuple' = return the result as a tuple (tb, ch1, ch2, mem, acq) 
                 'table' = return the result as a tale in markdown format
                 'text' = return the result as a multiline string which can be 
                          sent to the console or a file.
        '''
        
        def tupleToTable(tb, ch1, ch2, mem, acq):
            txt = ''

            def add(line):
                nonlocal txt
                if txt == '':
                    txt = line
                else:
                    txt = txt + '\n\r' + line

            def addChannel(ch,t):
                add(f"|{t}|Attenuation|{ch['att']}|")
                add(f"||Bandwidth limited|{ch['bw']}|")
                add(f"||Coupling|{ch['cpl']}|")
                add(f"||Offset (V)|{ch['offs']}|")
                add(f"||Skew (s)|{ch['skew']}|")
                add(f"||Trace|{ch['trace']}|")
                add(f"||Unit|{ch['unit']}|")
                add(f"||V/div|{ch['vdiv']}|")
                add(f"||Inverted|{ch['invert']}|")

            add('|Channel|Setting|Value|')
            add('|-|-|-|')
            add(f'||Timebase (s/div)|{tb}|')
            add(f'||Memory Depth|{mem}|')
            add(f'||Acquire|{acq[0]}|')
            add(f'||Samplerate (Sa/s)|{acq[1]}|')
            add('||||')
            addChannel(ch1,'CH1')
            add('||||')
            addChannel(ch2,'CH2')
            return txt
        
        def tupleToText(tb, ch1, ch2, mem, acq):
            txt = ''

            def add(line):
                nonlocal txt
                if txt == '':
                    txt = line
                else:
                    txt = txt + '\n\r' + line

            def addChannel(ch,t):
                add(f'Channel {t}')
                add('---------')
                add(f"Attenuation = {ch['att']}x")
                add(f"Bandwidth limited = {ch['bw']}")
                add(f"Coupling = {ch['cpl']}")
                add(f"Offset = {ch['offs']} V")
                add(f"Skew = {ch['skew']} s")
                add(f"Trace = {ch['trace']}")
                add(f"Unit = {ch['unit']}")
                add(f"V/div = {ch['vdiv']}")
                add(f"Inverted = {ch['invert']}")


            add(f'Timebase = {tb} s/div')
            add(f'Memory Depth = {mem} points')
            add(f'Acquire = {acq[0]}')
            add(f'Samplerate = {acq[1]} Sa/s')
            add('')
            addChannel(ch1,'1')
            add('')
            addChannel(ch1,'2')
            return txt
        
        ch1 = self.channelSettings(CH[0])
        ch2 = self.channelSettings(CH[1])
        tb = self.timebaseSettings()
        mem = self.memorySettings()
        acq = self.acquireSettings()
        match output:
            case 'tuple':
                return tb, ch1, ch2, mem, acq[0], acq[1]
            case 'table':
                return tupleToTable(tb, ch1, ch2, mem, acq)
            case 'text':
                return tupleToText(tb, ch1, ch2, mem, acq)
    

    def stop(self):
        '''
        Stops the acquisition of the oscilloscope. Note that a
        corresponding 'run' (or 'start') method, to start acquisition
        of the oscilloscope does not exist yet.

        Parameters:

        None

        Returns:

        None
        '''

        cmd = 'STOP'
        self.send(cmd)


    # This ('ARM') does not work
    # Not found a way to do it yet.
    def run(self):
        pass
