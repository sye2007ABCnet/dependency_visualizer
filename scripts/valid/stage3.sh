#!/usr/bin/env bash
# Этап 3. Корректные запуски: граф зависимостей, глубина, циклы.
# Тестовый репозиторий работает без интернета (код завершения везде 0).
# Запуск: bash scripts/valid/stage3.sh
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

F=fixtures

run "общая зависимость (ромб): D показана один раз" \
    -p A -r $F/simple.txt -t
run "другой корневой пакет" \
    -p C -r $F/simple.txt -t
run "цепочка, глубина по умолчанию 5" \
    -p A -r $F/chain.txt -t
run "цепочка, глубина 2" \
    -p A -r $F/chain.txt -t -d 2
run "цепочка, глубина 1 (только прямые зависимости)" \
    -p A -r $F/chain.txt -t -d 1
run "простой цикл" \
    -p A -r $F/cycle.txt -t
run "цикл не виден: не уместился в глубину" \
    -p A -r $F/cycle.txt -t -d 2
run "несколько циклов и самозависимость" \
    -p A -r $F/cycles.txt -t
run "вершина достигнута и глубоко, и близко (глубина 3)" \
    -p A -r $F/shortcut.txt -t -d 3
run "зависимость, которой нет в репозитории" \
    -p A -r $F/unknown.txt -t
