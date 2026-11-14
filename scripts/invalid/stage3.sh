#!/usr/bin/env bash
# Этап 3. Ошибочные запуски тестового репозитория (код завершения 1).
# Интернет не нужен. Запуск: bash scripts/invalid/stage3.sh
# Ошибки самих параметров (код 2) показывает scripts/invalid/stage1.sh.
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

F=fixtures

run "корневого пакета нет в файле" \
    -p Z -r $F/simple.txt -t
run "строка без двоеточия" \
    -p A -r $F/invalid/no_colon.txt -t
run "имя пакета маленькими буквами" \
    -p A -r $F/invalid/bad_name.txt -t
run "пакет описан дважды" \
    -p A -r $F/invalid/duplicate.txt -t
