#!/usr/bin/env bash
# Add to crontab with `crontab -e`

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
configs_dir="${repo_root}/configs"
email_logs_dir="${repo_root}/email_logs"
env_file="${repo_root}/.env"
uv_bin="/opt/homebrew/bin/uv"
debug_mode=false

if [ "${1:-}" = "--debug" ]; then
  debug_mode=true
elif [ "${#}" -gt 0 ]; then
  echo "Usage: $0 [--debug]" >&2
  exit 1
fi

if [ ! -x "${uv_bin}" ]; then
  echo "Missing uv binary: ${uv_bin}" >&2
  exit 1
fi

if [ ! -f "${env_file}" ]; then
  echo "Missing env file: ${env_file}" >&2
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

today_slug="$(date +%Y-%m-%d)"
failed_configs=()

# Sent emails are logged as timestamped HTML files with the config stem at the
# end. Use those logs as a restart marker so rerunning the script later in the
# day does not email the same recipient twice.
has_email_log_for_today() {
  local config_path="$1"
  local config_name
  local config_stem
  local config_slug

  config_name="$(basename "${config_path}")"
  config_stem="${config_name%.toml}"
  # Keep this in sync with safe_filename_part() in email_sender.py.
  config_slug="$(printf '%s' "${config_stem}" | sed -E 's/[^A-Za-z0-9._-]+/_/g; s/^[._-]+//; s/[._-]+$//')"
  if [ -z "${config_slug}" ]; then
    config_slug="config"
  fi

  compgen -G "${email_logs_dir}/${today_slug}T*_${config_slug}.html" > /dev/null
}

for config_path in "${config_paths[@]}"; do
  if has_email_log_for_today "${config_path}"; then
    echo "Skipping ${config_path}; email log already exists for ${today_slug}"
    continue
  fi

  echo "Running oxford-weekly for ${config_path}"
  command_args=(run oxford-weekly --config "${config_path}")
  if [ "${debug_mode}" = true ]; then
    command_args+=(--debug)
  fi

  if ! "${uv_bin}" "${command_args[@]}"; then
    echo "Failed: ${config_path}" >&2
    failed_configs+=("${config_path}")
  fi
done

if [ "${#failed_configs[@]}" -gt 0 ]; then
  echo "Failed configs:" >&2
  printf '  %s\n' "${failed_configs[@]}" >&2
  exit 1
fi
