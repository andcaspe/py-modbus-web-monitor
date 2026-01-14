# Docker

## Web app
Build and run the web app:
```bash
docker compose up --build
```
Open `http://localhost:8000/`.

## With simulated Modbus device
```bash
docker compose --profile sim up --build
```
The Compose file builds the UI with defaults targeting `sim:1502`.
