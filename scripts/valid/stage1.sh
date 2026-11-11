#!/usr/bin/env bash
# Этап 1. Корректные запуски: параметры разобраны и выведены как ключ=значение.
# Запуск: bash scripts/valid/stage1.sh (код завершения везде 0).
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

URL=http://archive.ubuntu.com/ubuntu

run "обязательные параметры" \
    -p curl -r "$URL" --package-version 7.81.0-1ubuntu1
run "все параметры" \
    -p curl -r "$URL" --package-version 7.81.0-1ubuntu1 -o out.svg -a -d 3
run "тестовый режим" \
    -p A -r fixtures/simple.txt -t
run "справка" \
    --help
