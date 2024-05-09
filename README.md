# pydatacq - Asynchronous Data Acquisition

With pydatacq you can collect data from a series of instruments. The drivers for specific instruments can be injected into the library. A driver for the SDS series of oscilloscopes from Siglent are included.

Data is acquired in an asynchronous way. Data collection is not blocking. So several instruments can be sampled at the same time, as well as calcuulation, display, storing etc of the sampled data.

Some demo progams (fft,thd,oscilloscope) are included in the package as well.

Short screen captures of sampling data and displaying them in a matplotlib window are present in the /resources folder.



## Classes

### LiveData

LiveData is the heart of the asynchronous data acquisition system. It performs the sampling of the instruments, and hands the data over to the so-called consumer of the data. It starts an asynchonous event-loop to handle all this asynchronously. It needs to be subclassed to connect to specific instruments.

#### get_data()
LiveData should be subclassed to provide a method `get_data()` to get the data from the instrument. One such sublass is provided, LiveSDS, which gets its data from Siglent oscilloscopes using SCPI.

#### Data consumer
Every LiveData (subclass) instance also needs a so-called 'consumer', which will receive the sampled data. The consumer can perform calculations, display, storage, redirection etc of the data. Consumers of the LiveData (subclass) usually live in the main application.

#### Data format
Format of the data is to the choice of the `get_data()` method. It is important that the data which is produced by `get_data()` is understood by the consumer. LiveData can optionally add a timestamp to the data. Also in this case, the consumer should understand the provided data.

#### Queue size
LiveData keeps a queue of datapackets which have not been processed by the consumer yet. LiveData will deliver the datapackets to its consumer in a first-in-first-out style.

LiveData can be told (upon instantiation) to keep a maximum amount of data packets in the queue. If acquisition of data is faster than the consumption of the data, memory may fill up with not yet consumed data packets. However, if a maximum queue size has been given, acquisition will stop (and yield control to the eventloop) until the queue size is less than the maximal size. 

If the queue size is unlimited, and the data acquisition (through the `get_data()` method) is blocking (ie. not asynchonous, not yielding control back to the eventloop) this will have to be informed on instantiation with `super().__init__(...,yields=False)`. This will instruct LiveData to pass control to the eventloop after every acquisition. This gives other tasks the chance to complete. If this is not done, the program may seem to hang, but still collect data and fill up memory. This may not occur often (ever). In the demo program `live_fm_sine.py` the LiveFMSine class is not yielding, it just computes a FM modulated sine, but in this case the maximum queue size is set to 1, so LiveData will still yield. If the queue size is set to unlimited, it is **essential** to set `yields=False` in the call to the super().__init__() return False.

#### Data acquisition rate
LiveData can print data acquisition rates on the console. This can be instructed upon instantiation. Data acquisition rates using scpi over ethernet have reached 60 data packets per second.

#### Event loop implementation
By default `LiveData` will use the `uvloop` event loop implementation which seems to be a lot faster than the default asyncio event loop. `uvloop` can be disabled by setting `use_uvloop=False` in the constructor arguments.


### LiveSDS

LiveSDS is an implementation of LiveData which collects data from the SDS series of oscilloscopes from Siglent. It can be told which channels to sample, and samples all these channels subsequently. Every wave packet returned by `get_data()` is prepended by the channel number. to be identifiable by the consumer later on.

LiveSDS makes use of the SDS class which talks asynchronous SCPI to the oscilloscope.

Upon instantiation LiveSDS needs to be told the ip address and the port on which the oscilloscope listens.

This class has only been tested on a SDS1202X-E oscilloscope. In theory it should work on SDS1000, SDS2000X and SDS2000X-E according to the Siglent programming manual (download at https://www.siglent.com/upload_file/document/SDS1000%20Series&SDS2000X&SDS2000X-E_ProgrammingGuide_PG01-E02D.pdf).


### SDS

This provides a thin class of common SCPI commands for the SDS1000, SDS200X and SDS200X-E series of osclloscopes from Siglent.

This class has only been tested on the SDS1202X-E model.

See the "SDS1000 Series & SDS2000X & SDS2000X-E ProgrammingGuide PG01-E02D.pdf" which can be downloaded from https://www.siglent.com/upload_file/document/SDS1000%20Series&SDS2000X&SDS2000X-E_ProgrammingGuide_PG01-E02D.pdf

The class has highlevel methods to

- asynchronous sampling of a channel to get the waveform data
- synchronous sampling of a channel to get the waveform data
- set the timebase
- get the number of divisions on the oscilloscope display
- get the channel settings (attenuation, bandwidth, coupling, offset, skew, trace, unit, volts per division, inverted), all of these in text, tuple or markdown table format.

By virtue of the base class Siglent it provides basic scpi methods to

- asynchronously query the device
- synchronously query the device
- asynchronously send a command to the devive
- synchronously send a command to the devive

The method `async_getwave()` takes care not to overflow the oscilloscope with requests for wavedata. On slower timebases the requests may come faster than the oscciloscope can acquire a new waveform. In that case, without precautions, the oscilloscope may seem to hang, or respond irratically. The method `async_getwave()` compares the oscilloscopes timebase (times the number of horizontal divisions) with the time it has been since the latest data request. `async_getwave()` waits until (4 * timebase * divisions) seconds have passed since the latest request to post a new request. The factor of 4 has been found experimentally to give the best performance.


### LiveWindow

LiveWindow is a class which shows a matplotlib window and provides a small blitting framework. On instantiation it shows a empty non-blocking matplotlib window. Its `draw()` method draws artists which have been prepared by clients on top of the empty graph by way of blitting. This is the fastest way matplotlib offers. Other graphing frameworks may offer faster ways of updating graphs.

It offers a callback method to be notified when the window has been closed.

It handles resizes of the window well.

To clients it offers access to the windows ax and fig attributes for special operations like title, axis and ticks changes.

LiveWindow is an example class which implements a so called 'consumer' for the LiveData class. It accepts datapackets from LiveData and shows them (after processing by LiveWindow's `process_cb` processing callback function) in a matplotlib window. 


## Demo programs

### fft.py

`fft.py` will show an FFT from one channel on the Siglent socilloscope. The program gets its data from a Siglent oscilloscope, but is easily adapted to other data sources.

See the output of the --help argument below for all the options.

The `fft.py` program understands '1MHz' and interpretes it as 1.000.000 Hz, '1kHz' as 1000 Hz and so on. For this it uses the `Quantiphy` package.

`fft.py` will recognize it when there is no adequate data in the waveform to calculate the requested fft frequency range and display this in the top of the screen.

A screen capture of the fft spectrum of the FM radio band is shown in the /resources folder.

```
$ python fft.py --help
usage: fft.py [-h] -C {1,2} [-a AVERAGE] [-H] -c CENTRE -s SPAN [-m MIN] [-M MAX] -ip IP [-port PORT] [-t NAME] [-w NAME] [-fps]
              [-tc {0,1}]

Display FFT for a channel on Siglent oscilloscope.

options:
  -h, --help            show this help message and exit
  -C {1,2}              channel to display (default: None)
  -a AVERAGE, --average AVERAGE
                        Averaging (default: 1)
  -H, --maxhold         Max hold (default: False)
  -c CENTRE, --centre CENTRE
                        Centre frequency (Hz) (default: None)
  -s SPAN, --span SPAN  Span (Hz) (default: None)
  -m MIN, --min MIN     Min power (dBvrms) (default: -120)
  -M MAX, --max MAX     Max power (dBvrms) (default: -40)
  -ip IP                ip address of the oscilloscope (default: None)
  -port PORT            port on which the oscilloscope is listening (default: 5025)
  -t NAME, --title NAME
                        plot title (default: None)
  -w NAME, --window NAME
                        window title (default: None)
  -fps                  show waveform updates per second (default: False)
  -tc {0,1}, --triggercoupling {0,1}
                        1 = set channel coupling to AC and set trigger source to fft channel, trigger type to edge triggering, trigger
                        level to 50%, trigger hold to off and trigger mode to auto, 0 = do not set (default: 1)
```


### thd.py

`thd.py` will calculate the Total Harmonic Distortion (THD) from a signal given its fundamental frequency. The program gets its data from a Siglent oscilloscope, but is easily adapted to other data sources.

See the output of the --help argument below for all the options.

The `thd.py` program understands '1MHz' and interpretes it as 1.000.000 Hz, '1kHz' as 1000 Hz and so on. For this it uses the `Quantiphy` package.

A screen capture of the fft of a 1kHz signal showing its THD is shown in the /resources folder.

```
$ python thd.py --help
usage: thd.py [-h] -C {1,2} [-f0 FREQ] [-max_f FREQ] [-f FLOOR] -ip IP [-port PORT] [-t NAME] [-w NAME] [-fps]

Display FFT and calculate THD for a channel on Siglent SDS1202X-E oscilloscope.

options:
  -h, --help            show this help message and exit
  -C {1,2}              channel to display (default: None)
  -f0 FREQ              fundamental frequency (in Hz) (default: 1k)
  -max_f FREQ           maximum frequency to display / use for calculations (in Hz) (default: 25k)
  -f FLOOR, --floor FLOOR
                        minimum level of harmonics (in dBvrms) (default: -85)
  -ip IP                ip address of the oscilloscope (default: None)
  -port PORT            port on which the oscilloscope is listening (default: 5025)
  -t NAME, --title NAME
                        plot title (default: None)
  -w NAME, --window NAME
                        window title (default: None)
  -fps                  show waveform updates per second (default: False)
```

### osc.py

The `osc.py` program displays waveforms from the oscilloscope in a matplotlib window.

See the output of the --help argument below for all the options.

```
$ python osc.py --help
usage: osc.py [-h] -C CHANNELS -ip IP [-port PORT] [-t NAME] [-w NAME] [-fps]

Display FFT and calculate THD for a channel on Siglent SDS1202X-E oscilloscope.

options:
  -h, --help            show this help message and exit
  -C CHANNELS           channels to display (default: None)
  -ip IP                ip address of the oscilloscope (default: None)
  -port PORT            port on which the oscilloscope is listening (default: 5025)
  -t NAME, --title NAME
                        plot title (default: None)
  -w NAME, --window NAME
                        window title (default: None)
  -fps                  show waveform updates per second (default: False)
```

### demo_fm_sine

The `demo_fm_sine.py` program shows the application of a different data source (LiveFMSine) than the Siglent oscilloscope from the previous demo programs. In this case the data source is class LiveFMSine which calculates the waveform a an FM modulated sinewave. The waveform is shown in a matplotlib window.

LiveFMSine's `get_data()` is an example of a blocking `get_data()` method, it does not yield control back to the eventloop. This could cause other tasks in the eventloop not to get time to execute if the maximum queue size is unlimited. Reason for this is that `asyncio.Queue.put()` does not yield when the queue is unlimited. There are two ways to prevent this happening:

- limiting the max queue size. In this case Queue.put() will yield when the queue has reached max size.
- let `yields=False` in the call to the `super().__init__()` to signal LiveData that the `get_data()` does not yield and LiveData needs to do that.

In LiveFMSine both methods are used. Experiment with this to see the results when not doing it properly.

An screen recording of `live_fm_sine.py` output is in the /resources folder.


## Requirements

### os

Development and testing have been done on a Fedora 39 box with Gnome 45.


### Python

The package and demo programs have been tested with python version 3.11.


### uvloop

The `uvloop` package is used as an alternative to asyncio's event loop implementation. It appears to be much faster. Version 0.19.0 has been used for development and testing.


### matplotlib

`matplotlib` is used in all the demo programs and is essential for the `LiveWindow` class. Version 3.8.4 has been used for development and testing.


### numpy

`numpy` is used in all the demo programs. Version 1.26.4 has been used for development and testing. It is not required for the data acquisition framework although it is hard to imagine running it without `numpy`.


### scipy

`scipy` is used in the `fft_calculations` module. This is only important when running the `fft.py` or `thd.py` demo programs.


### quantiphy

The `quantiphy` package is used in the demo programs to allow for friendly frequency input. Version 2.19 has been used for development and testing.


## Installation

## Usage

