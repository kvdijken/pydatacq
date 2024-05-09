import asyncio
from time import asctime
from abc import ABC, abstractmethod

import uvloop


#
class LiveData(ABC):
    '''
    Produces live data from a device. This live data
    is produced asynchronously and can be processed asynchonously
    in a 'consumer' function. The 'consumer' can be injected
    into this class at instantiation. The 'consumer' function
    could do any of the following  with the data from the
    device (not exhaustive):

    - display the data in a graph
    - perform calculations on the data
    - send the data to another device.
    - save the data to a file
    - ...

    The 'consumer' is set by the consumer_cb argument of the constructor.
    The 'producer' is a subclass of LiveData.

    The method to get the data from the device is an abstract
    method 'get_data()' which must be overridden in subclasses
    of LiveData.

    This class implements a First-In-First_Out queue for the data
    packets which are generated. The maximum size of the queue can
    be set upon instantiation.

    By default the uvloop implementation for the event loop will be
    used because of its higher speed. This can be disabled at
    instantiation of the class.
    '''

    _go_on = True
    __updates = 0

    # interval for fps display
    __fps_interval = 1 # seconds
    __consumer_cb = None

    #
    def __init__(self,consumer_cb,id=None,fps=False,queue_maxsize=1,
                 timestamp=False,use_uvloop=True,yields=True):
        '''
        This does not start the data acquisition yet. Use start() for that.

        Parameters:

        consumer_cb : The consumer of the data packets. The function should have 
                      signature consumer(data) or consumer(self,data), where the
                      format for data is up to the data producer.
        id : id of this data producer. If None, the name of the class will be used.
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
        self.__consumer_cb = consumer_cb
        if use_uvloop:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.__fps = fps
        self.__queue_maxsize = queue_maxsize
        self.__timestamp = timestamp
        self._yields = yields
        self._id = id if id is not None else type(self).__name__
    

    #
    def start(self):
        '''
        Starts the data acquisition.
        '''
        self._go_on = True
        asyncio.run(self._loop())
    

    #
    def stop(self):
        '''
        Stops the data acquisition.
        '''
        self._go_on = False


    @abstractmethod
    async def get_data(self):
        '''
        Gets data from the device. Must be overridden
        and implemented in subclass for the specific device.
        The format of the data returned by this method may
        be defined by the method itself, as long as the
        consumer understands this format.

        For example, produce (channel,wavedata) for an oscilloscope.
        '''
        return None


    # obtains waveforms and puts the newest in the queue.
    async def _produce_data(self,queue):
        '''
        see: https://bugs.python.org/issue43119

        This method will always yield if 
        yields has been set properly in __init__().
        '''
        while self._go_on:
            # get the data
            data = await self.get_data()

            # ensure yield
            if not self._yields:
                # force yield
                await asyncio.sleep(0)

            # put data in queue
            if data is not None:
                if self.__timestamp:
                    await queue.put(asctime(),data)
                else:
                    await queue.put(data)
            

    # consumes waveforms obtained from the queue
    async def _consume_data(self,queue):
        '''
        Dispatches the data packets to the consumer.
        '''
        while self._go_on:
            data = await queue.get()
            # get the data out of the queue as fast as possible.
            queue.task_done()
            self.__updates = self.__updates + 1
            if self.__consumer_cb is not None:
                await self.__consumer_cb(data)


    # 
    async def _show_fps(self):
        if self.__updates > 0:
            fps = self.__updates / self.__fps_interval
            print(f'{self._id}: fps = {int(fps)}')
            self.__updates = 0
    

    # 
    async def _show_fps_timer(self):
        while self._go_on:
            # This construct is to ensure that the
            # printing itself does not affect the
            # time interval. The sleep() and shwo_fps()
            # are started at the same time, and the 
            # interval is fixed by the sleep() method.
            await asyncio.gather(
                asyncio.sleep(self.__fps_interval),
                self._show_fps()
            )
    

    async def _loop(self):
        '''
        Runs the main loop
        '''
        queue = asyncio.Queue(maxsize=self.__queue_maxsize)
        tasks = [
            asyncio.create_task(self._produce_data(queue)),
            asyncio.create_task(self._consume_data(queue))
        ]
        # If fps is requested, add a task which prints
        # fps on the console.
        if self.__fps:
            tasks.append(asyncio.create_task(self._show_fps_timer()))
        await asyncio.gather(*tasks)
