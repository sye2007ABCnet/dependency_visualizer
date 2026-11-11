#!/usr/bin/env bash
# Этап 1. Ошибочные запуски: для каждого параметра своя ошибка.
# Запуск: bash scripts/invalid/stage1.sh (код завершения везде 2).
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

URL=http://x.org

run "нет имени пакета" \
    -r "$URL"
run "неверное имя пакета" \
    -p Bad_Name -r "$URL" --package-version 1.0
run "строчная буква в тестовом режиме" \
    -p a -r fixtures/simple.txt -t
run "репозиторий не является URL" \
    -p curl -r archive --package-version 1.0
run "файл тестового репозитория не найден" \
    -p A -r /no/file.txt -t
run "нет версии пакета" \
    -p curl -r "$URL"
run "неверная версия пакета" \
    -p curl -r "$URL" --package-version abc
run "изображение не .svg" \
    -p curl -r "$URL" --package-version 1.0 -o g.png
run "нет каталога для изображения" \
    -p curl -r "$URL" --package-version 1.0 -o /no/dir/g.svg
run "глубина не число" \
    -p curl -r "$URL" --package-version 1.0 -d abc
run "глубина меньше 1" \
    -p curl -r "$URL" --package-version 1.0 -d 0
run "много ошибок сразу" \
    -p Bad_Name -r archive -o g.png -d 0
