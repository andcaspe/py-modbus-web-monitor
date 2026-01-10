# Notebooks

`notebooks/modbus_readings_analysis.ipynb` loads the latest SQLite log from `outputs/`
(or a specific path you set in the notebook), plots the series, and adds basic
anomaly detection.

Suggested dependencies:
- `pandas`
- `matplotlib`
- `jupyter`
- Optional: `statsmodels` (`pip install -e ".[ml]"`)

Install via extras:
- `pip install -e ".[notebooks]"`
