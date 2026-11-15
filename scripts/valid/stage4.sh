#!/usr/bin/env bash
# Этап 4. Порядок загрузки зависимостей на тестовых репозиториях.
# Интернет не нужен, код завершения везде 0.
# Запуск: bash scripts/valid/stage4.sh
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

F=fixtures

run "общая зависимость (ромб): D загружается первой" \
    -p A -r $F/simple.txt -t
run "слои: общие зависимости раньше зависимых" \
    -p A -r $F/layers.txt -t
run "цепочка загружается с конца" \
    -p A -r $F/chain.txt -t
run "цепочка, глубина 2: порядок неполный" \
    -p A -r $F/chain.txt -t -d 2
run "простой цикл: одно ребро пропущено" \
    -p A -r $F/cycle.txt -t
run "несколько циклов и самозависимость" \
    -p A -r $F/cycles.txt -t
run "зависимость, которой нет в репозитории" \
    -p A -r $F/unknown.txt -t
run "другой корневой пакет" \
    -p C -r $F/layers.txt -t
