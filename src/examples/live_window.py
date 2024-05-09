# see: https://stackoverflow.com/questions/8955869/why-is-plotting-with-matplotlib-so-slow

import asyncio

import matplotlib as mpl
import matplotlib.pyplot as plt
# import matplotlib_rc

#
class LiveWindow():
    '''
    Shows a non-blocking matplotlib window.
    Artists can be presented to the draw() method
    where they will be shown by blitting.
    '''

    fig = None
    ax = None

    #
    def __init__(self,windowTitle=None,plotTitle=None,onclose_cb=None):
        '''
        Parameters:

        windowTitle : title of the matplotlib window
        plotTitle : title of the plot
        onclose_cb : method to call when the window has been closed.
                     The signature should be onclose(event)
        '''
        self.fig, self.ax = plt.subplots(num=windowTitle)
        self.fig.canvas.mpl_connect('close_event', self._on_close)
        self.__onclose_cb = onclose_cb
        self.fig.canvas.mpl_connect('resize_event', self._on_resize)
        plt.show(block=False)
        plt.grid(True,alpha=0.3)
        if plotTitle is not None:
            plt.title(plotTitle)
    

    #
    bg = None
    async def draw(self,artist):
        '''
        Draws the artist(s) by way of blitting.
        The artists should have been prepared by

        ax.plot(..., animated=True)

        where ax is the ax attribute of this class.
        '''
        # Make sure we have an empty background to start with.
        if self.bg is None:
            self.fig.canvas.draw()
            plt.pause(0.1)
            self.bg = self.fig.canvas.copy_from_bbox(self.ax.bbox)

        # Now restore the empty background and redraw the changed artists.
        if artist is not None:
            self.fig.canvas.restore_region(self.bg)
            # convert artist to iterable artists
            try:
                _ = iter(artist)
                artists = artist
            except TypeError:
                artists = [artist]
            for a in artists:
                if a is not None:
                    self.ax.draw_artist(a)
        self.fig.canvas.blit(self.ax.bbox)
        self.fig.canvas.flush_events()


    #
    def redraw(self):
        '''
        Force a redraw of the entire figure.
        This may be used in the following
        example cases:
         
        - one of the axes has changed
          and the ticks need to be redrawn.
        - the title has changed

        Returns: None
        '''
        self.bg = None


    #
    def _on_close(self,event):
        '''
        This will be called upon closing of the window.
        Calls the onclose_cb method given to __init__().
        '''
        if self.__onclose_cb is not None:
            self.__onclose_cb(event)


    #
    def _on_resize(self,event):
        # This will force the background and axes to be redrawn again
        self.redraw()
