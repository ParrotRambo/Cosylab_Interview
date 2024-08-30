import argparse
import asyncio
import json
import logging
import socket
import sys


class Client(asyncio.Protocol):

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.transport = None
        self.send_task = None

        # Initialization of logger
        self.log = logging.getLogger('Client')
        handler = logging.StreamHandler(sys.stdout)

        # Datetime formatting setup
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

        self.send(json.dumps({
            'type': 'client'
        }))

        self.send_task = asyncio.create_task(self.send_data())

        self.log.info('Connection made')

    def connection_lost(self, exc):
        self.log.info('Connection lost')
        if exc:
            self.log.error(f'Error: {exc}')

    def data_received(self, data: bytes):
        self.log.info('Data received')
        data = data.decode('utf-8').strip()
        data = data.split('\n')

        for d in data:
            try:
                json_obj = json.loads(d)

                print(json_obj[0])
                for row in json_obj[1:]:
                    print('\t'.join(row))
                print()
            except ValueError as e:
                print(d)
                print()

    async def send_data(self):
        """
        Event loop for sending commands from stdout
        """
        while True:
            data = await self.loop.run_in_executor(None, input, ">")
            self.send(data)

    def send(self, data: str):
        data += '\n'
        try:
            self.transport.write(data.encode())
        except socket.error as e:
            self.log.error(f"Socket error while sending data: {e}")
            self.transport.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='New client setup')
    parser.add_argument('--addr', help='Server address', required=False, default='127.0.0.1')
    parser.add_argument('--port', help='Server port', required=False, default=50000)
    args = parser.parse_args()
    
    loop = asyncio.get_event_loop()
    client = Client(loop=loop)
    coro = loop.create_connection(lambda: client, args.addr, args.port)
    loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task(loop)]
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
