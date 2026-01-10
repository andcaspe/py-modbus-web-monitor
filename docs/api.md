# API

## WebSocket protocol (`/ws/monitor`)

### First message (required)
```json
{
  "type": "configure",
  "connection": {"protocol": "tcp", "host": "127.0.0.1", "port": 502, "unitId": 1},
  "interval": 1.0,
  "targets": [
    {"kind": "holding", "address": 0, "count": 1, "label": "Reg 0"}
  ]
}
```

### Updates
```json
{
  "type": "update",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": [
    {"address": 0, "kind": "holding", "label": "Reg 0", "values": [123]}
  ]
}
```

### Writes
```json
{"type": "write", "writes": [{"kind": "holding", "address": 10, "value": 42}]}
```
For coils, values are coerced from booleans/0/1; multiple values are supported with lists.

## REST endpoints

### `POST /api/modbus/read`
```json
{
  "connection": {"protocol": "tcp", "host": "127.0.0.1", "port": 502, "unitId": 1},
  "targets": [{"kind": "coil", "address": 0, "count": 4}]
}
```
Returns `{"data": [{"address": 0, "kind": "coil", "label": "...", "values": [true, false, ...]}]}`.

### `POST /api/modbus/write`
```json
{
  "connection": {"protocol": "tcp", "host": "127.0.0.1", "port": 502, "unitId": 1},
  "writes": [{"kind": "holding", "address": 15, "value": [1, 2, 3]}]
}
```

### `POST /api/anomaly/zscore`
Computes z-scores from logged readings (no live Modbus read).
```json
{
  "connection": {"protocol": "tcp", "host": "127.0.0.1", "port": 502, "unitId": 1},
  "targets": [{"kind": "holding", "address": 0, "count": 1}],
  "window": 60,
  "min_samples": 10
}
```
Returns the latest value, z-score, and sample counts per target value.

### `POST /api/anomaly/stl`
Uses STL decomposition to compute z-scores from residuals.
Requires `statsmodels` (`pip install -e ".[ml]"`).
Same payload as `/api/anomaly/zscore`.
