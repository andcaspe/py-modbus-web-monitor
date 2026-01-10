# Simulated Modbus Server

Run a local Modbus TCP device with changing registers/coils:
```bash
pip install -e .
modbus-sim-server --port 1502 --period 0.5  # defaults: host=127.0.0.1, port=1502, period=1s
```
Holding/input registers vary over time; coils/discrete inputs flip each tick.

## Fault injection + sine wave signals
```bash
modbus-sim-server \
  --holding-signal sine \
  --input-signal sine \
  --fault-enable \
  --fault-mode drop \
  --fault-kind input \
  --fault-addresses 0 \
  --fault-every 20 \
  --fault-duration 5 \
  --fault-magnitude 400
```

Set a target cycle length for sine waves (e.g., 2 seconds per full cycle):
```bash
modbus-sim-server --input-signal sine --holding-signal sine --period 0.1 --cycle-seconds 2
```

## Fault profiles
```bash
modbus-sim-server --fault-profile sine_drop
```
Available profiles: `sine_drop`, `sensor_drift`, `compressor`.
Each profile also ships default outlier settings you can enable with `--outlier-enable`.

Example: profile + outliers enabled:
```bash
modbus-sim-server --fault-profile sine_drop --outlier-enable
```

## Point-wise outliers
```bash
modbus-sim-server \
  --holding-signal sine \
  --input-signal sine \
  --outlier-enable \
  --outlier-kind holding \
  --outlier-addresses 0-3 \
  --outlier-probability 0.1 \
  --outlier-mode random \
  --outlier-magnitude 350
```
