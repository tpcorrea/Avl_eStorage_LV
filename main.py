import os
from application import Application
import asyncio

import can


def main():
    app = Application()

    loop = asyncio.get_event_loop()
    notifier = can.Notifier(app.bus, app.listeners, loop=loop)

    loop.create_task(app._run())
    loop.run_forever()


if __name__ == "__main__":
    main()
