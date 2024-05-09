import asyncio

class Siglent():

    def __init__(self,ip,port):
        self.ip = ip
        self.port = port


    async def async_query(self,cmd,size=8000):
        '''Perform an asynchronous query. Can be used for
        strings and for binary data, although for binary
        data it may be better to use a special purpose function
        which knows the protocol for the binary data.
        
        Parameters:
        
        Returns:
        
        '''
        reader, writer = await asyncio.open_connection(self.ip,self.port)

        try:
            b_cmd = bytes(cmd,'ascii')
            writer.write(b_cmd + b'\n')
            await writer.drain()
            data = await reader.read(size)
    #        data = await reader.read()
        finally:
            writer.close()
            await writer.wait_closed()
        return data


    def query(self,cmd,size=8000):
        '''Perform a synchronous query. Can be used
        to perform queries which return strings, like *IDN?'''
        data = asyncio.run(self.async_query(cmd,size))
        return data
    

    def query_string(self,cmd,size=8000):
        '''Perform a synchronous query for a string result.
        
        Parameters:
        
        cmd : (str) command to be sent to the device.
        
        Returns:
        
        The string (str) returned from the device.'''
        return self.query(cmd).decode('ascii')


    async def async_send(self,cmd):
        '''
        '''
        _, writer = await asyncio.open_connection(self.ip,self.port)
        b_cmd = bytes(cmd,'ascii')
        writer.write(b_cmd + b'\n')
        await writer.drain()
        writer.close()
        await writer.wait_closed()


    def send(self,cmd):
        '''
        '''
        asyncio.run(self.async_send(cmd))
