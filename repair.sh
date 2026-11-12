#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
    PYTHON="${PYTHON_BIN:-python3}"
fi

REPORT="$ROOT_DIR/logs/startup-report.txt"

if [[ -f "$ROOT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.env"
    set +a
fi

curl_check() {
    local label="$1"
    local url="$2"
    local header="${3:-}"
    local status

    if [[ -n "$header" ]]; then
        status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --max-time 10 --config - <<EOF
url = "$url"
header = "$header"
EOF
)" || status="000"
    else
        status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --max-time 10 "$url")" || status="000"
    fi

    if [[ "$status" =~ ^2[0-9][0-9]$ ]]; then
        printf '[OK] %s (HTTP %s)\n' "$label" "$status"
    else
        printf '[SKIP] %s (HTTP %s)\n' "$label" "$status"
    fi
}

check_internet_services() {
    if ! command -v curl >/dev/null 2>&1; then
        printf '[SKIP] curl is not installed; install curl to run network checks.\n'
        return
    fi

    printf '\nInternet service checks\n'
    curl_check 'Discord internet access' 'https://discord.com/api/v10/gateway'
    [[ -n "${SUPERCELL_ROYALE_API:-}" ]] && curl_check 'Supercell Clash Royale' 'https://proxy.royaleapi.dev/v1/locations' "Authorization: Bearer ${SUPERCELL_ROYALE_API}"
    [[ -n "${SUPERCELL_COC_API:-}" ]] && curl_check 'Supercell Clash of Clans' 'https://cocproxy.royaleapi.dev/v1/locations' "Authorization: Bearer ${SUPERCELL_COC_API}"
    [[ -n "${SUPERCELL_BRAWL_STARS_API:-}" ]] && curl_check 'Supercell Brawl Stars' 'https://bsproxy.royaleapi.dev/v1/locations' "Authorization: Bearer ${SUPERCELL_BRAWL_STARS_API}"
    [[ -n "${NEWS_API_KEY:-}" ]] && curl_check 'News API' 'https://newsapi.org/v2/top-headlines?country=us&pageSize=1' "X-Api-Key: ${NEWS_API_KEY}"
    [[ -n "${NASA_API_KEY:-}" ]] && curl_check 'NASA API' "https://api.nasa.gov/planetary/apod?api_key=${NASA_API_KEY}"
    [[ -n "${OPEN_WEATHER_API_KEY:-}" ]] && curl_check 'OpenWeather API' "https://api.openweathermap.org/data/2.5/weather?q=London&appid=${OPEN_WEATHER_API_KEY}"
    [[ -n "${IMAGE_FLIP_KEY:-}" ]] && curl_check 'Imgflip API' 'https://api.imgflip.com/get_memes' "Authorization: Bearer ${IMAGE_FLIP_KEY}"
}

show_report() {
    if [[ -f "$REPORT" ]]; then
        printf '\n%s\n' "Startup report"
        cat "$REPORT"
    else
        printf '\nNo startup report found yet.\n'
    fi
}

install_group() {
    local label="$1"
    shift
    printf '\nInstalling %s...\n' "$label"
    "$PYTHON" -m pip install "$@"
}

set_env_value() {
    local name="$1"
    local secret="$2"
    local value
    if [[ "$secret" == "true" ]]; then
        read -r -s -p "Enter ${name} (hidden, leave blank to skip): " value
    else
        read -r -p "Enter ${name} (leave blank to skip): " value
    fi
    printf '\n'
    if [[ -n "$value" ]]; then
        touch "$ROOT_DIR/.env"
        sed -i "/^${name}=.*/d" "$ROOT_DIR/.env"
        printf '%s=%s\n' "$name" "$value" >> "$ROOT_DIR/.env"
        printf '%s was written to .env.\n' "$name"
    fi
}

configure_discord() {
    set_env_value DISCORD_BOT_TOKEN true
}

configure_database() {
    set_env_value MONGO_URI true
    set_env_value REDIS_HOST false
    set_env_value REDIS_PORT false
}

configure_lavalink() {
    set_env_value LAVALINK_PASSWORD true
}

configure_supercell() {
    set_env_value SUPERCELL_ROYALE_API true
    set_env_value SUPERCELL_COC_API true
    set_env_value SUPERCELL_BRAWL_STARS_API true
}

configure_api_keys() {
    set_env_value NEWS_API_KEY true
    set_env_value NASA_API_KEY true
    set_env_value OPEN_WEATHER_API_KEY true
    set_env_value IMAGE_FLIP_KEY true
}

show_report
printf '\nChoose a repair action:\n'
printf '  1) Configure Discord bot token\n'
printf '  2) Install and configure MongoDB/Redis support\n'
printf '  3) Install and configure Lavalink support\n'
printf '  4) Configure all Supercell API keys\n'
printf '  5) Configure News/NASA/Weather/Imgflip API keys\n'
printf '  6) Install Jishaku and autoreload support\n'
printf '  7) Install the full requirements file\n'
printf '  8) Re-run the package/configuration audit\n'
printf '  0) Exit\n'
read -r -p 'Selection: ' choice

case "$choice" in
    1) configure_discord ;;
    2)
        install_group "database and cache support" pymongo 'redis[hiredis]'
        configure_database
        ;;
    3)
        install_group "music support" pomice
        configure_lavalink
        ;;
    4) configure_supercell ;;
    5) configure_api_keys ;;
    6) install_group "developer support" 'jishaku[procinfo]' watchfiles ;;
    7) install_group "full requirements" -r "$ROOT_DIR/requirements.txt" ;;
    8) ;;
    0) exit 0 ;;
    *) printf 'Unknown selection.\n'; exit 2 ;;
esac

if [[ "$choice" != "0" ]]; then
    printf '\nRe-running startup audit...\n'
    (cd "$ROOT_DIR" && "$PYTHON" -c 'from pathlib import Path; from core.startup import audit_startup; audit_startup(Path("logs/startup-report.txt"))')
    show_report
    check_internet_services
fi
