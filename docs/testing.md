# Testing and CI

The project includes integration tests that verify the REST API and WebSocket functionality using a simulated Modbus server.

## Running tests locally
1. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
2. Run the test suite:
   ```bash
   python tests/run_all.py
   ```
   This generates Allure results in `outputs/allure-results`.

3. View Allure report (optional):
   ```bash
   allure serve outputs/allure-results
   ```

## Continuous integration
On every push to `main` or `master`, GitHub Actions automatically:
- Runs integration tests across Python 3.10, 3.11, and 3.12.
- Runs frontend tests (Vitest).
- Generates a unified Allure report.
- Deploys the report to GitHub Pages.

Live test report: https://andcaspe.github.io/py-modbus-web-monitor/
