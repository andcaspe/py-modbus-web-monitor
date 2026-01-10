import json

import pytest
from fastapi.testclient import TestClient

from modbus_web_monitor.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_websocket_monitor(client, modbus_server):
    host, port = modbus_server
    with client.websocket_connect("/ws/monitor") as websocket:
        # 1. Send configuration
        config = {
            "type": "configure",
            "connection": {"protocol": "tcp", "host": host, "port": port, "unitId": 1},
            "interval": 0.2,
            "targets": [
                {"kind": "holding", "address": 0, "count": 1, "label": "Reg 0"}
            ],
        }
        websocket.send_text(json.dumps(config))

        # 2. Receive status message
        status = websocket.receive_json()
        assert status["type"] == "status"
        assert "Config set" in status["message"]

        # 3. Receive at least one update
        # Sometimes there might be a small delay, let's wait for 'update' type
        update = None
        for _ in range(5):
            msg = websocket.receive_json()
            if msg["type"] == "update":
                update = msg
                break

        assert update is not None
        assert update["type"] == "update"
        assert "data" in update
        assert len(update["data"]) == 1
        assert update["data"][0]["address"] == 0


def test_websocket_write_through_monitor(client, modbus_server):
    host, port = modbus_server
    with client.websocket_connect("/ws/monitor") as websocket:
        # 1. Configure
        config = {
            "type": "configure",
            "connection": {"protocol": "tcp", "host": host, "port": port, "unitId": 1},
            "targets": [{"kind": "holding", "address": 60, "count": 1}],
        }
        websocket.send_json(config)
        websocket.receive_json()  # skip status

        # 2. Send write command
        write_cmd = {
            "type": "write",
            "writes": [{"kind": "holding", "address": 60, "value": 555}],
        }
        websocket.send_json(write_cmd)

        # 3. Wait for an update that reflects the write (or just check next update)
        # Note: it might take a cycle to see the new value
        found = False
        for _ in range(5):
            update = websocket.receive_json()
            if update["type"] == "update":
                for entry in update["data"]:
                    if entry["address"] == 60 and entry["values"][0] == 555:
                        found = True
                        break
            if found:
                break
        assert found


def test_websocket_invalid_first_message(client):
    with client.websocket_connect("/ws/monitor") as websocket:
        websocket.send_json({"type": "ping"})
        msg = websocket.receive_json()
        assert msg["type"] == "error"
        assert "First message must be a 'configure' command" in msg["message"]
