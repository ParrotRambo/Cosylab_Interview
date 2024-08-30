import argparse
import asyncio
import json
import random
import os
import logging
import socket
import sys


class Archive(asyncio.Protocol):

    def __init__(self, loop: asyncio.AbstractEventLoop, filepath: str = None):
        self.loop = loop
        self.transport = None

        if filepath is None:
            filepath = f'./archives/archive{random.randint(1, 10000)}.txt'
        self.filepath = filepath

        # Open file for writing at the start
        self.file = open(self.filepath, 'a+')
        if os.stat(self.filepath).st_size == 0:
            self.file.write('\t'.join(['Timestamp', 'ID', 'Sensor_Type', 'Value']))
            self.file.write('\n')

        # Initialization of logger
        self.log = logging.getLogger('Archive')
        handler = logging.StreamHandler(sys.stdout)

        # Datetime formatting setup
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

        self.send(json.dumps({
            'type': 'archive'
        }))

        self.log.info('Connection made')

    def connection_lost(self, exc):
        self.log.info('Connection lost')
        self.file.close()  # Close the file when connection is lost
        if exc:
            self.log.error(f'Error: {exc}')

    def data_received(self, data: bytes):
        data = data.decode('utf-8').strip()
        data = self.parse_msg(data)

        for row in data:
            self.file.write('\t'.join([row[0]] + row[1]))
            self.file.write('\n')

    def parse_msg(self, data):
        data = data.split('\n')
        return [json.loads(d) for d in data]

    def send(self, data: str):
        data += '\n'
        try:
            self.transport.write(data.encode())
            self.log.info(f'Sent data {data}')
        except socket.error as e:
            self.log.error(f"Socket error while sending data: {e}")
            self.transport.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='New archive setup')
    parser.add_argument('--addr', help='Server address', required=False, default='127.0.0.1')
    parser.add_argument('--port', help='Server port', required=False, default=50000)
    args = parser.parse_args()
    
    loop = asyncio.get_event_loop()
    archive = Archive(loop=loop)
    coro = loop.create_connection(lambda: archive, args.addr, args.port)
    loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        archive.file.close()
        tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task(loop)]
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
