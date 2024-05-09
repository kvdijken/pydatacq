from sds import SDS
from pydatacq import LiveData


#
class LiveSDS(LiveData):
    '''
    Produces live data from an Siglent SDS1202X-E oscilloscope. This
    live data is produced asynchronously and can be processed in a
    'consumer' function which can be designated by setting the
    consumer_cb argument of the constructor. The 'consumer' function
    could do any of the following with the data from the SDS
    (not exhaustive):

    - display in a graph
    - perform calculations
    - send the data to another device.
    '''


    #
    def __init__(self,id,ip,port,channels,consumer_cb,fps=False,queue_maxsize=1,
                 timestamp=False,use_uvloop=True,yields=True):
        '''
        Initialises communication with the oscilloscope

        Parameters:

        id : id of this data producer. If None, the name of the class will be used.
        ip : IP address of the SDS device
        port : port on which the SDS device is listening (usually 5025)
        channels : Set of channels to sample (0-based).
        consumer_cb : The consumer of the data packets. The function should have 
                    signature consumer(data) or consumer(self,data), where the
                    format for data is up to the data producer.
        fps : if True, show frames per second in the console.
        queue_maxsize : Determines the maximum size of the queue. Default = 1.
                        Note that the queue size may be unbounded, but only
                        for non-blocking data-producers. This is by nature 
                        of the not always cooperative scheduling of Queue.put()
                        (see: https://bugs.python.org/issue43119).
                        The demo data-producer LiveFMSine is an example of a
                        blocking data producer. 

                        Data-producers which get their data in another way
                        (for example over ethernet) may use 'await' on an
                        asyncio IO operation, but that does not garantee that
                        these operations are non-blocking. Pythons await
                        does not garantee cooperative scheduling.

                        Besides that for blocking data-producers the size of
                        the queue MUST be bounded, there may be no practical
                        use for an unbounded queue.
        timestamp : include a timestamp on every datapacket. In that case
                    get_data() will return a tuple (str,data), where str
                    is the time as returned by time.asctime().
        use_uvloop : if True will use uvloop as its event loop implementation
                     which seems to be faster that the default asyncio
                     event loop. If False, will use asyncio's event loop.
        yields :    Should return False if get_data() never yields.
        '''
        super().__init__(consumer_cb=consumer_cb,id=id,fps=fps,queue_maxsize=queue_maxsize,
                         timestamp=timestamp,use_uvloop=use_uvloop,yields=yields)
        self.sds = SDS(ip,port)
        if type(channels) == int:
            self.channels = {channels}
        else:
            self.channels = channels
        self._next = self._next_channel()

    
    # 
    def _next_channel(self):
        '''
        Yields the next channel for which to retrieve data.
        It cycles through all the channels in self.channels.
        '''
        while super()._go_on:
            for ch in self.channels:
                yield ch
        yield None


    # 
    async def get_data(self):
        '''
        Gets a waveform from the oscilloscope.
        All channels which are mentioned in self.channels
        are retrieved sequentially.
        '''
        ch = next(self._next)
        if ch is None:
            return None
        wave = await self.sds.async_getwave_x(ch) # wave = (t,v)
        return (ch,wave)

