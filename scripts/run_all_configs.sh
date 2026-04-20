#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
configs_dir="${repo_root}/configs"
env_file="${repo_root}/.env"
uv_bin="/opt/homebrew/bin/uv"

if [ ! -f "${env_file}" ]; then
  echo "Missing env file: ${env_file}" >&2
  exit 1
fi

if [ ! -x "${uv_bin}" ]; then
  echo "Missing uv binary: ${uv_bin}" >&2
  exit 1
fi

shopt -s nullglob
config_paths=("${configs_dir}"/*.toml)

if [ "${#config_paths[@]}" -eq 0 ]; then
  echo "No config files found in ${configs_dir}" >&2
  exit 1
fi

set -a
. "${env_file}"
set +a

if [ -z "${RESEND_API_KEY:-}" ]; then
  echo "RESEND_API_KEY is not set" >&2
  exit 1
fi

cd "${repo_root}"

for config_path in "${config_paths[@]}"; do
  echo "Running oxford-weekly for ${config_path}"
  "${uv_bin}" run oxford-weekly --config "${config_path}"
done
