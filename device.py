import argparse
import asyncio
import logging
import random
import json
import socket
import sys


class Device(asyncio.Protocol):

    def __init__(self, device_type: str, state: str, rate: float, loop: asyncio.AbstractEventLoop):
        self.type = device_type
        self.rate = rate
        self.state = state
        self.loop = loop
        
        self.send_task = None
        self.transport = None

        # Initialization of logger
        self.log = logging.getLogger('Device')
        handler = logging.StreamHandler(sys.stdout)

        # Datetime formatting setup
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport

        self.send(json.dumps({
            'type': 'device',
            'measurement': self.type,
            'state': self.state
        }))

        if self.state == 'on':
            self.send_task = asyncio.create_task(self.send_data())

        self.log.info('Connection made')

    def connection_lost(self, exc):
        self.log.info('Connection lost')
        if exc:
            self.log.error(f'Error: {exc}')
        self.change_state('off')

    def data_received(self, data: bytes):
        self.log.info('Data received')
        data = data.decode('utf-8').strip()
        self.change_state(data)

    def change_state(self, state: str):
        """
        Change state of the device

        :param state: state of the device to change to
        """
        if state not in ['on', 'off']:
            return
        
        self.log.info(f'Changed state to {state}')
        self.state = state

        if state == 'on' and self.send_task is None:
            self.send_task = asyncio.create_task(self.send_data())
        elif state == 'off' and self.send_task is not None:
            msg = self.send_task.cancel()
            self.send_task = None

            self.log.info(f'Cancelling send_task: {msg}')

    async def send_data(self):
        """
        Event loop for sending dummy data
        """
        self.log.info('Starting send data loop')

        while True:
            number = random.uniform(0, 100)
            self.send(str(number))
            await asyncio.sleep(self.rate)

    def send(self, data: str):
        data += '\n'
        try:
            self.transport.write(data.encode())
            self.log.info(f'Sent data {data}')
        except socket.error as e:
            self.log.error(f"Socket error while sending data: {e}")
            self.transport.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='New device setup')
    parser.add_argument('--type', help='Type of the device (e.g. temp, pres, hum, rad)', required=True)
    parser.add_argument('--rate', help='Rate of data transfer in seconds', required=False, default=3, type=float)
    parser.add_argument('--state', help='Starting state of the device (e.g. on, off)', required=False, default='on')
    parser.add_argument('--addr', help='Server address', required=False, default='127.0.0.1')
    parser.add_argument('--port', help='Server port', required=False, default=50000)
    args = parser.parse_args()
    
    loop = asyncio.get_event_loop()
    device = Device(device_type=args.type, state=args.state, rate=args.rate, loop=loop)
    coro = loop.create_connection(lambda: device, args.addr, args.port)
    loop.run_until_complete(coro)
    
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        device.send_task.cancel()
        tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task(loop)]
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
