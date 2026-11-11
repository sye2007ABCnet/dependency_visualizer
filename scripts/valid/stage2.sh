#!/usr/bin/env bash
# Этап 2. Корректные запуски: прямые зависимости из настоящего репозитория.
# Нужен интернет (индекс весит около 1,8 МБ). Код завершения везде 0.
# Запуск: bash scripts/valid/stage2.sh
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

URL=http://archive.ubuntu.com/ubuntu
UPDATES="$URL/dists/jammy-updates/main/binary-amd64/Packages.xz"

run "простые зависимости" \
    -p curl -r "$URL" --package-version 7.81.0-1
run "эпоха в версии и два ограничения на один пакет" \
    -p git -r "$URL" --package-version 1:2.34.1-1ubuntu1
run "Pre-Depends" \
    -p python3 -r "$URL" --package-version 3.10.4-0ubuntu2
run "прямая ссылка на индекс .xz из jammy-updates" \
    -p curl -r "$UPDATES" --package-version 7.81.0-1ubuntu1.30
