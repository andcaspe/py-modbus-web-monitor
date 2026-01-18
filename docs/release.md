# Release workflow
This project publishes a GitHub Release and a Python package to GitHub Packages
when a Git tag matching `v*` is pushed.

## What the workflow does
The workflow at `.github/workflows/release.yml`:
- Builds the frontend and syncs assets into the Python package
  (`scripts/sync_web_assets.sh`).
- Builds the wheel/sdist (`python -m build`).
- Publishes to GitHub Packages (`pip.pkg.github.com`).
- Builds release notes from `debian/changelog` using `dpkg-parsechangelog`.
- Creates a GitHub Release and attaches the `dist/*` artifacts.

## Debian changelog (release notes source)
Release notes come from the top entry in `debian/changelog`.
The workflow fails if `debian/changelog` is missing.

Create/update it with `dch` (from `devscripts`):
```bash
sudo apt-get update && sudo apt-get install -y devscripts

mkdir -p debian
dch --create --package py-modbus-web-monitor \
    --newversion 0.1.0-1 \
    --distribution unstable \
    --urgency medium \
    "Initial Debian changelog entry."
```

Add new entries:
```bash
dch -v 0.2.0-1 "Describe the change"
```

Check the latest entry:
```bash
dpkg-parsechangelog -l debian/changelog -S Changes
```

## Tagging a release
1) Update the package version in `pyproject.toml` to match the tag.
2) Update `debian/changelog` with the new entry.
3) Push a tag (e.g., `v0.2.0`).
