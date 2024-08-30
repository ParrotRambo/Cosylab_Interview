import argparse
import asyncio
import json
import random
import socket
import logging
import sys


class Monitor(asyncio.Protocol):

    def __init__(self, loop: asyncio.AbstractEventLoop, filepath: str = None):
        self.loop = loop
        self.transport = None

        self.limits = {
            'temp': [10., 90.],
            'rad': [10., 90.],
            'pres': [10., 90.],
            'hum': [10., 90.]
        }

        if filepath is None:
            filepath = f'./monitors/monitor{random.randint(1, 10000)}.txt'
        self.filepath = filepath

        # Open file for writing at the start
        self.file = open(self.filepath, 'a+')

        # Initialization of logger
        self.log = logging.getLogger('Monitor')
        handler = logging.StreamHandler(sys.stdout)

        # Datetime formatting setup
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

        self.send(json.dumps({
            'type': 'monitor'
        }))

        self.log.info('Connection made')

    def data_received(self, data: bytes):
        data = data.decode('utf-8').strip()
        data = self.parse_msg(data)

        alarms = []
        for row in data:
            row = row[1]
            if row[1] not in self.limits:
                continue

            if float(row[-1]) > self.limits[row[1]][1]:
                alarms.append('ALARM: Value too large: {} Sensor: {} ID: {}'.format(row[-1], row[1], row[0]))
            elif float(row[-1]) < self.limits[row[1]][0]:
                alarms.append('ALARM: Value too small: {} Sensor: {} ID: {}'.format(row[-1], row[1], row[0]))

        if alarms:
            for row in alarms:
                self.log.warning(row)
                self.file.write(row)
                self.file.write('\n')
            self.send('\n'.join(alarms))

    def connection_lost(self, exc):
        self.log.info('Connection lost')
        self.file.close()  # Close the file when connection is lost
        if exc:
            self.log.error(f'Error: {exc}')

    def parse_msg(self, data: str):
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
    parser = argparse.ArgumentParser(description='New monitor setup')
    parser.add_argument('--addr', help='Server address', required=False, default='127.0.0.1')
    parser.add_argument('--port', help='Server port', required=False, default=50000)
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    monitor = Monitor(loop=loop)
    coro = loop.create_connection(lambda: monitor, args.addr, args.port)
    loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        monitor.file.close()  # Ensure the file is closed when program is interrupted
        tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task(loop)]
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
