#!/usr/bin/env bash
# Этап 2. Ошибочные запуски: ошибки получения данных (код завершения 1).
# Нужен интернет. Запуск: bash scripts/invalid/stage2.sh
# Ошибки самих параметров (код 2) показывает scripts/invalid/stage1.sh.
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

URL=http://archive.ubuntu.com/ubuntu

run "нет такой версии пакета" \
    -p curl -r "$URL" --package-version 7.81.0-1ubuntu1
run "нет такого пакета" \
    -p nosuchpkg -r "$URL" --package-version 1.0
run "репозиторий отвечает 404" \
    -p curl -r http://archive.ubuntu.com/nothing --package-version 1.0
run "сервер не существует" \
    -p curl -r http://no-such-host.invalid --package-version 1.0
run "тестовый режим ещё не реализован (появится на этапе 3)" \
    -p A -r fixtures/simple.txt -t
