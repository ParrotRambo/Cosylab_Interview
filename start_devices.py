from device import Device
import asyncio
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='New device setup')
    parser.add_argument('--rate', help='Rate of data transfer in seconds', required=False, default=3, type=float)
    parser.add_argument('--state', help='Starting state of the device (e.g. on, off)', required=False, default='on')
    parser.add_argument('--addr', help='Server address', required=False, default='127.0.0.1')
    parser.add_argument('--port', help='Server port', required=False, default=50000)
    parser.add_argument('--num_temp', help='Number of temperature sensors', required=False, default=2)
    parser.add_argument('--num_rad', help='Number of radiation sensors', required=False, default=2)
    parser.add_argument('--num_pres', help='Number of pressure sensors', required=False, default=2)
    parser.add_argument('--num_hum', help='Number of humidity sensors', required=False, default=2)
    args = parser.parse_args()

    device_types = ['rad'] * args.num_rad + ['hum'] * args.num_hum + ['pres'] * args.num_pres + ['temp'] * args.num_temp

    loop = asyncio.get_event_loop()
    for device_type in device_types:
        device = Device(device_type=device_type, state=args.state, rate=args.rate, loop=loop)
        coro = loop.create_connection(lambda: device, args.addr, args.port)
        loop.run_until_complete(coro)

    loop.run_forever()
    
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task(loop)]
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()

