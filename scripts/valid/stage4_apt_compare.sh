#!/usr/bin/env bash
# Этап 4. Сверка порядка загрузки со штатным apt.
# apt моделирует установку на пустую систему (-s ничего не меняет, права
# root не нужны), рекомендуемые пакеты не учитываются. Список пакетов
# берётся только из раздела main выпуска, как и у программы.
# Нужны Ubuntu и интернет, архитектура amd64.
# Запуск: bash scripts/valid/stage4_apt_compare.sh [пакет]
# Другой выпуск: CODENAME=jammy bash scripts/valid/stage4_apt_compare.sh curl
source "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"

PACKAGE="${1:-curl}"
CODENAME="${CODENAME:-$(lsb_release -cs)}"
MIRROR=http://archive.ubuntu.com/ubuntu
KEYRING=/usr/share/keyrings/ubuntu-archive-keyring.gpg
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/lists/partial" "$WORK/cache/archives/partial"
echo "deb [arch=amd64 signed-by=$KEYRING] $MIRROR $CODENAME main" \
    > "$WORK/sources.list"
cat > "$WORK/apt.conf" <<CONF
Dir::Etc::sourcelist "$WORK/sources.list";
Dir::Etc::sourceparts "/dev/null";
Dir::State::lists "$WORK/lists";
Dir::Cache "$WORK/cache";
Dir::State::status "/dev/null";
APT::Install-Recommends "false";
APT::Architectures "amd64";
CONF
export APT_CONFIG="$WORK/apt.conf"

apt-get update > /dev/null || { echo "ошибка: apt update" >&2; exit 1; }
VERSION="$(apt-cache show "$PACKAGE" 2> /dev/null \
    | awk '/^Version:/ {print $2; exit}')"
if [ -z "$VERSION" ]; then
    echo "ошибка: пакет '$PACKAGE' не найден в $CODENAME/main" >&2
    exit 1
fi
INDEX="$MIRROR/dists/$CODENAME/main/binary-amd64/Packages.gz"

python3 src/main.py -p "$PACKAGE" -r "$INDEX" \
    --package-version "$VERSION" -d 100 > "$WORK/ours.txt" 2> /dev/null
awk '/^ +[0-9]+\. / {print $2}' "$WORK/ours.txt" > "$WORK/ours.list"
apt-get -s install "$PACKAGE" | awk '/^Inst / {print $2}' > "$WORK/apt.list"

echo "=== $PACKAGE $VERSION ($CODENAME/main)"
echo "пакетов в порядке загрузки: программа $(wc -l < "$WORK/ours.list"),"\
    "apt $(wc -l < "$WORK/apt.list")"
show_ours() {
    # Строки программы для пакетов из stdin: номер, имя и пометки.
    while read -r name; do
        awk -v n="$name" '/^ +[0-9]+\. / && $2 == n' "$WORK/ours.txt"
    done
}

echo "=== только в выводе программы:"
comm -23 <(sort "$WORK/ours.list") <(sort "$WORK/apt.list") | show_ours
echo "=== только в выводе apt:"
comm -13 <(sort "$WORK/ours.list") <(sort "$WORK/apt.list")
echo "=== порядок apt нарушает рёбра графа (кроме пропущенных из-за циклов):"
awk '
    FNR == NR { position[$1] = FNR; next }
    /^Граф зависимостей/ { section = "graph"; next }
    /^Пакетов в графе/ { section = ""; next }
    /^Рёбра, пропущенные/ { section = "skipped"; next }
    /^Порядок неполный/ { section = ""; next }
    section == "graph" && $2 == "->" {
        for (i = 3; i <= NF; i++) {
            dep = $i; gsub(/,/, "", dep)
            count++; from[count] = $1; to[count] = dep
        }
    }
    section == "skipped" && $2 == "->" { skipped[$1, $3] = 1 }
    END {
        found = 0
        for (i = 1; i <= count; i++) {
            if (!(from[i] in position) || !(to[i] in position)) continue
            if (position[to[i]] > position[from[i]] \
                && !((from[i], to[i]) in skipped)) {
                print "  " from[i] " -> " to[i]; found++
            }
        }
        if (!found) print "  нет"
    }
' "$WORK/apt.list" "$WORK/ours.txt"
echo "=== первые 8 пакетов: программа | apt"
paste -d'|' <(head -8 "$WORK/ours.list") <(head -8 "$WORK/apt.list")
