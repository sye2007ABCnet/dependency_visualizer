#!/usr/bin/env bash
# Этап 2. Сверка со штатным apt: список зависимостей должен совпасть.
# Нужны Ubuntu и интернет. Пакет можно передать аргументом (по умолчанию
# curl). Поддерживаются пакеты из компонента main, архитектура amd64.
# Запуск: bash scripts/valid/stage2_apt_compare.sh [пакет]
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

PACKAGE="${1:-curl}"
CODENAME="$(lsb_release -cs)"
VERSION="$(apt-cache show "$PACKAGE" | awk '/^Version:/ {print $2; exit}')"
BASE=http://archive.ubuntu.com/ubuntu/dists

if [ -z "$VERSION" ]; then
    echo "ошибка: apt не знает пакет '$PACKAGE'" >&2
    exit 1
fi

echo "=== штатный apt: $PACKAGE $VERSION ($CODENAME)"
apt-cache show "$PACKAGE=$VERSION" | grep -E '^(Pre-Depends|Depends):' \
    | awk '!seen[$0]++'
echo

echo "=== наша программа"
# Версия из apt лежит не в «чистом» выпуске, а в -updates или -security,
# поэтому перебираем индексы по очереди.
for pocket in "$CODENAME-updates" "$CODENAME-security" "$CODENAME"; do
    index="$BASE/$pocket/main/binary-amd64/Packages.gz"
    if python3 src/main.py -p "$PACKAGE" -r "$index" \
        --package-version "$VERSION" 2>/dev/null; then
        echo "(индекс: $index)"
        exit 0
    fi
done
echo "ошибка: версия $VERSION не найдена в индексах (или нет сети)" >&2
exit 1
