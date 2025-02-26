import asyncio
import traceback
import socket
import time


class Siglent():

    b_term = b'\r\n'
    
    # 
    def __init__(self,ip,port,wait=0):
        self.ip = ip
        self.port = int(port)
        self._wait = wait


    # 
    async def async_query(self,cmd,size=8000):
        '''
        Perform an asynchronous query. Can be used for
        strings and for binary data, although for binary
        data it may be better to use a special purpose function
        which knows the protocol for the binary data.
        
        Parameters:

        cmd : (str) command to be sent to the device.
        
        Returns:
        
        Returns the data in the format as defined by the device.
        '''
        reader, writer = await asyncio.open_connection(self.ip,self.port)
        try:
            b_cmd = bytes(cmd,'ascii')
            writer.write(b_cmd + self.b_term)
            await writer.drain()
            data = await reader.read(size)
        finally:
            writer.close()
            await writer.wait_closed()
            if self._wait > 0:
                await asyncio.sleep(self._wait)
        return data


    # 
    def query(self,cmd,size=8000):
        '''
        Perform a synchronous query. Can be used
        to perform queries which return strings, like *IDN?

        Parameters:

        cmd : (str) query to be sent to the device

        Returns:
        
        Returns the data in the format as defined by the device.
        '''
        data = asyncio.run(self.async_query(cmd,size))
        return data
    

    # 
    def query_string(self,cmd,size=8000):
        '''
        Perform a synchronous query for a string result.
        
        Parameters:
        
        cmd : (str) command to be sent to the device.
        
        
        Returns:
        
        The string (str) returned from the device.
        '''
        return self.query(cmd).decode('ascii')


    # 
    async def async_send(self,cmd):
        '''
        Asynchronously sends a command to the device.

        Parameters:

        cmd : (str) command to be sent to the device.
        '''
        _, writer = await asyncio.open_connection(self.ip,self.port)
        # b_cmd = bytes(cmd,'ascii')
        # writer.write(b_cmd + self.b_term)
        b_cmd = bytes(cmd + self.b_term,'ascii')
        writer.write(b_cmd)
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        if self._wait > 0:
            await asyncio.sleep(self._wait)


    # 
    def send(self,cmd):
        '''
        Synchronously sends a command to the device.
        This method communicates synchronously
        over sockets and may be used when an
        asyncio event loop is running.

        Parameters:

        cmd : (str) command to be sent to the device.
        '''
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _sock:
                _sock.connect((self.ip,self.port))
                _sock.setblocking(True)
                b_cmd = bytes(cmd,'ascii')
                _sock.sendall(b_cmd + self.b_term)
                _sock.close()
                if self._wait > 0:
                    time.sleep(self._wait)
        except:
            traceback.print_exc()
            
