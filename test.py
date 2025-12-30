import asyncio
from pymodbus.client import AsyncModbusTcpClient

async def main():
    client = AsyncModbusTcpClient("127.0.0.1", port=1502, timeout=2)
    await client.connect()
    resp = await client.read_holding_registers(0, device_id=1)
    print("OK" if not resp.isError() else f"Error: {resp}")
    await client.close()

asyncio.run(main())
