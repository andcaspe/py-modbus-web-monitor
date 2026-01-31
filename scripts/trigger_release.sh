#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 1
fi

if [[ ! -f pyproject.toml ]]; then
  echo "Error: pyproject.toml not found" >&2
  exit 1
fi

version="$(
  awk '
    /^\[project\]$/ { in_project=1; next }
    /^\[/ { in_project=0 }
    in_project && $1 == "version" {
      gsub(/"/, "", $3)
      print $3
      exit
    }
  ' pyproject.toml
)"

if [[ -z "${version}" ]]; then
  echo "Error: project.version not found in pyproject.toml" >&2
  exit 1
fi

tag="v${version}"

if [[ ! "$tag" =~ ^v[0-9]+(\.[0-9]+){1,2}([.-][0-9A-Za-z]+)?$ ]]; then
  echo "Error: tag must look like vX.Y.Z (e.g., v0.1.1)" >&2
  exit 1
fi

if ! rg -q "^[^ ]+ \\(${version}\\)" debian/changelog; then
  echo "Error: debian/changelog has no entry for version ${version}" >&2
  exit 1
fi

if git rev-parse -q --verify "refs/tags/${tag}" >/dev/null; then
  echo "Error: tag ${tag} already exists" >&2
  exit 1
fi

git tag "$tag"
git push origin "$tag"
