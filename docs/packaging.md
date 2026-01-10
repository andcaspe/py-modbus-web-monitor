# Packaging

- Install/editable: `pip install -e .`
- Build wheel/sdist: `python -m build` (requires `build` or use `hatch build`)
- CLI entrypoint: `py-modbus-web-monitor` runs `uvicorn py_modbus_web_monitor.api:app`
- Bundle the built UI into the Python package: `scripts/sync_web_assets.sh`

To include the UI in a wheel/sdist, run `scripts/sync_web_assets.sh` before `python -m build`.

## Debian package (bundled deps)
Build a `.deb` that includes a venv + the compiled frontend UI:
```bash
scripts/build_deb.sh
sudo dpkg -i build/deb/py-modbus-web-monitor_0.1.0_amd64.deb
py-modbus-web-monitor
```

Optional overrides:
- `DEB_MAINTAINER="Name <email>"` (control file)
- `DEB_VERSION=0.1.0+local1` (package version)
- `BUILD_DIR=build/deb` (output dir)

Runtime overrides:
- `py-modbus-web-monitor --host 127.0.0.1 --port 8000`
- Or set `MODBUS_WEB_MONITOR_HOST` / `MODBUS_WEB_MONITOR_PORT`
