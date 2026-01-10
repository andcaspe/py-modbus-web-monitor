import asyncio
import pytest
from modbus_web_monitor.utils.sim_server import run_simulated_server
import threading
import time
import socket

def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def modbus_server():
    host = "127.0.0.1"
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    # We use a mutable container to signal the server to stop
    status = {"running": True}

    def run_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        server_task = loop.create_task(run_simulated_server(host, port, period=0.1))

        async def wait_for_stop():
            while status["running"]:
                await asyncio.sleep(0.1)
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
            loop.stop()

        loop.create_task(wait_for_stop())
        loop.run_forever()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # Wait for the server to start
    timeout = 5
    start_time = time.time()
    while not is_port_open(host, port):
        if time.time() - start_time > timeout:
            pytest.fail("Simulated Modbus server failed to start")
        time.sleep(0.1)

    yield host, port

    status["running"] = False
    thread.join(timeout=2)
