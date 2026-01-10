# Data logging (SQLite)

By default, holding/input readings are logged to a per monitor session file named like:
`outputs/modbus_readings_YYYY-MM-DD_HH-mm-ss.sqlite` (local time).

Environment overrides:
- `MODBUS_WEB_MONITOR_LOG_ENABLED=false` to disable logging
- `MODBUS_WEB_MONITOR_LOG_KINDS=holding,input` (or `all`)
