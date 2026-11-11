#!/usr/bin/env bash
# Общие функции для скриптов ручной проверки.
# Подключается командой: source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

# Переходим в корень проекта: скрипты можно запускать из любого каталога.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

# run "описание" опции... - запускает программу и показывает код завершения.
run() {
    local title="$1"
    shift
    echo "=== $title"
    echo "\$ python3 src/main.py $*"
    python3 src/main.py "$@"
    echo "[код завершения: $?]"
    echo
}
