import logging
import asyncio
import json
import uuid
import datetime
import argparse
import socket
import sys


class AggrServer:

    def __init__(self, loop: asyncio.AbstractEventLoop, addr: str, port: int):
        self.client_list = {}
        self.device_list = {}
        self.archive_list = {}
        self.monitor_list = {}
        self.broadcast_task = None

        # Initialization of logger
        self.log = logging.getLogger('AggrServer')
        handler = logging.StreamHandler(sys.stdout)

        # Datetime formatting setup
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)

        self.log.info('Started server')

        self.server = loop.run_until_complete(asyncio.start_server(self.accept_connection, addr, port))

    async def send(self, writer: asyncio.StreamWriter, data: str):
        """
        Sending data to the connected client
        """
        data += '\n'
        try:
            writer.write(data.encode())
            await writer.drain()  # await to ensure task completion
        except socket.error as e:
            self.log.error(f"Socket error while sending data: {e}")

    async def broadcast_to_devices(self, data: list[str]):
        if len(data) < 2 or data[1] not in ['on', 'off']:
            return

        for device_id in self.device_list:
            reader, writer, device_type = self.device_list[device_id]
            if data[0] == device_type:
                await self.send(writer, data[1])

    async def broadcast_to_clients(self, data: str):
        for reader, writer in self.client_list.values():
            await self.send(writer, data)

    async def broadcast_to_monitors(self, data: str):
        for reader, writer in self.monitor_list.values():
            await self.send(writer, data)

    async def broadcast_to_archives(self, data: str):
        for reader, writer in self.archive_list.values():
            await self.send(writer, data)

    async def handle_client(self, device_id: str, reader: asyncio.StreamReader):
        """
        Handle the client response
        """
        self.log.info(f'Handling client: {device_id}')
        while True:
            try:
                data = (await reader.readline()).decode('utf-8').strip()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.warning(f'Error while reading from client {device_id}: {e}')
                break

            if not data:
                del self.client_list[device_id]
                break

            self.log.info(f'Client {device_id} data received: {data}')
            data = data.split(' ')
            if len(data) == 2:
                await self.broadcast_to_devices(data)

        writer = self.client_list.get(device_id, None)
        if writer:
            try:
                writer[1].close()
                await writer[1].wait_closed()
            except Exception as e:
                self.log.error(f'Error closing connection for client {device_id}: {e}')

    async def handle_archive(self, device_id: str, reader: asyncio.StreamReader):
        """
        Handle the archive response
        """
        self.log.info(f'Handling archive: {device_id}')
        while True:
            try:
                data = (await reader.readline()).decode('utf-8').strip()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.warning(f'Error while reading from archive {device_id}: {e}')
                break

            if not data:
                del self.archive_list[device_id]
                break

        writer = self.archive_list.get(device_id, None)
        if writer:
            try:
                writer[1].close()
                await writer[1].wait_closed()
            except Exception as e:
                self.log.error(f'Error closing connection for archive {device_id}: {e}')

    async def handle_monitor(self, device_id: str, reader: asyncio.StreamReader):
        """
        Handle the monitor response and send alarms to clients if any
        """
        self.log.info(f'Handling monitor: {device_id}')
        while True:
            try:
                data = (await reader.readline()).decode('utf-8').strip()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.warning(f'Error while reading from monitor {device_id}: {e}')
                break

            if not data:
                del self.monitor_list[device_id]
                break

            if data.split(' ')[0] == 'ALARM:':
                await self.broadcast_to_clients(data)

        writer = self.monitor_list.get(device_id, None)
        if writer:
            try:
                writer[1].close()
                await writer[1].wait_closed()
            except Exception as e:
                self.log.error(f'Error closing connection for monitor {device_id}: {e}')

    async def handle_device(self, device_id: str, reader: asyncio.StreamReader):
        """
        Broadcast the values from device
        """
        self.log.info(f'Handling device: {device_id}')
        while True:
            try:
                date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data = (await reader.readline()).decode('utf-8').strip()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.warning(f'Error while reading from device {device_id}: {e}')
                break

            if not data:
                del self.device_list[device_id]
                break

            data = [date, (device_id, self.device_list[device_id][-1], data)]
            data = json.dumps(data)

            self.log.info(data)

            await asyncio.gather(
                self.broadcast_to_clients(data),
                self.broadcast_to_archives(data),
                self.broadcast_to_monitors(data),
                return_exceptions=True
            )

        writer = self.device_list.get(device_id, None)
        if writer:
            try:
                writer[1].close()
                await writer[1].wait_closed()
            except Exception as e:
                self.log.error(f'Error closing connection for device {device_id}: {e}')

    async def get_conn_type(self, reader: asyncio.StreamReader):
        """
        Get the type of client connecting (monitor, archive, client, device)
        """
        try:
            data = (await reader.readline()).decode('utf-8').strip()
            if not data:
                return None
            return json.loads(data)
        except (asyncio.CancelledError, json.JSONDecodeError, Exception) as e:
            self.log.warning(f'Error while getting connection type: {e}')
            return None

    async def accept_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Accept a new connection and assign it a new device_id
        """
        connection = await self.get_conn_type(reader)
        if connection is not None and 'type' in connection:
            self.log.info(f'New connection established: {connection["type"]}')

            device_id = str(uuid.uuid4())

            if connection['type'] == 'client':
                self.client_list[device_id] = (reader, writer)
                await self.handle_client(device_id, reader)

            elif connection['type'] == 'archive':
                self.archive_list[device_id] = (reader, writer)
                await self.handle_archive(device_id, reader)

            elif connection['type'] == 'monitor':
                self.monitor_list[device_id] = (reader, writer)
                await self.handle_monitor(device_id, reader)

            elif connection['type'] == 'device':
                self.device_list[device_id] = (reader, writer, connection['measurement'])
                await self.handle_device(device_id, reader)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='New archive setup')
    parser.add_argument('--addr', help='Server address', required=False, default='0.0.0.0')
    parser.add_argument('--port', help='Server port', required=False, default=50000)
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    server = AggrServer(loop, args.addr, int(args.port))
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task(loop)]
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
