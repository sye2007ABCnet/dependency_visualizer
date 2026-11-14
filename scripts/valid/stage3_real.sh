#!/usr/bin/env bash
# Этап 3. Граф зависимостей из настоящего репозитория Ubuntu.
# Нужен интернет (индекс весит около 1,8 МБ). Код завершения везде 0.
# В выводе видны настоящие циклы: libc6 <-> libgcc-s1, libc6 <-> libcrypt1.
# Запуск: bash scripts/valid/stage3_real.sh
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

URL=http://archive.ubuntu.com/ubuntu

run "curl, прямые зависимости (глубина 1)" \
    -p curl -r "$URL" --package-version 7.81.0-1 -d 1
run "curl, глубина 3" \
    -p curl -r "$URL" --package-version 7.81.0-1 -d 3
run "git, глубина по умолчанию 5" \
    -p git -r "$URL" --package-version 1:2.34.1-1ubuntu1
