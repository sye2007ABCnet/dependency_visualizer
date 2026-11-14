"""
Источники данных о зависимостях для построения графа.

AptSource берёт зависимости из индекса пакетов Ubuntu, FileSource — из
тестового репозитория (текстовый файл с описанием графа). Оба источника
отвечают на один вопрос: какие прямые зависимости у пакета.
"""

from apt_repo import (
    RepositoryError,
    build_index_url,
    select_stanza,
    build_package_table
)
from config import TEST_PACKAGE_RE
from dependencies import direct_dependencies

COMMENT_PREFIX = "#"
NAME_SEPARATOR = ":"


class AptSource:
    """Зависимости пакетов из индекса репозитория Ubuntu.

    У корневого пакета берётся запись заданной версии. Остальные
    пакеты ищутся по имени: в индексе одного выпуска у пакета, как
    правило, одна версия, поэтому ограничения версий не проверяются.
    Из группы альтернатив выбирается первая, которая есть в индексе
    (так поступает и apt); если нет ни одной, берётся первая по списку.
    """

    def __init__(self, index_text, root, version):
        """Разбирает индекс и находит запись корневого пакета."""
        self._table = build_package_table(index_text)
        self._root = root
        self._root_stanza = select_stanza(
            self._table.get(root, []), root, version
        )

    def dependencies(self, name):
        """Возвращает имена прямых зависимостей или None, если нет пакета."""
        stanza = self._find(name)
        if stanza is None:
            return None
        names = (self._choose(group) for group in direct_dependencies(stanza))
        return tuple(dict.fromkeys(names))

    def _find(self, name):
        """Возвращает запись пакета в индексе или None."""
        if name == self._root:
            return self._root_stanza
        stanzas = self._table.get(name)
        return stanzas[0] if stanzas else None

    def _choose(self, group):
        """Выбирает имя пакета из группы альтернатив."""
        for alternative in group.alternatives:
            if alternative.name in self._table:
                return alternative.name
        return group.alternatives[0].name


class FileSource:
    """Зависимости пакетов из тестового репозитория."""

    def __init__(self, packages, root):
        """Проверяет, что корневой пакет описан в тестовом репозитории."""
        if root not in packages:
            raise RepositoryError(
                f"пакет '{root}' не найден в тестовом репозитории"
            )
        self._packages = packages

    def dependencies(self, name):
        """Возвращает зависимости пакета или None, если он не описан."""
        return self._packages.get(name)


def _parse_line(line, number):
    """Разбирает строку 'ПАКЕТ: ЗАВИСИМОСТЬ ...' в пару (имя, кортеж)."""
    name, separator, rest = line.partition(NAME_SEPARATOR)
    if not separator:
        raise RepositoryError(
            f"строка {number}: ожидается 'ПАКЕТ: зависимости', "
            f"получено '{line}'"
        )
    name = name.strip()
    dependencies = rest.split()
    for item in [name] + dependencies:
        if not TEST_PACKAGE_RE.match(item):
            raise RepositoryError(
                f"строка {number}: имя '{item}' недопустимо: пакеты "
                "называются большими латинскими буквами"
            )
    return name, tuple(dict.fromkeys(dependencies))


def parse_test_repository(text):
    """Разбирает описание тестового репозитория в словарь.

    Формат: по строке на пакет, 'A: B C'. Пустые строки и строки,
    начинающиеся с '#', пропускаются. Ключ словаря — имя пакета,
    значение — кортеж его зависимостей. Бросает RepositoryError
    с номером строки, если описание некорректно.
    """
    packages = {}
    for number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith(COMMENT_PREFIX):
            continue
        name, dependencies = _parse_line(line, number)
        if name in packages:
            raise RepositoryError(
                f"строка {number}: пакет '{name}' описан повторно"
            )
        packages[name] = dependencies
    return packages


def load_test_repository(path):
    """Читает файл тестового репозитория и возвращает словарь пакетов."""
    try:
        with open(path, encoding="utf-8") as source:
            text = source.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise RepositoryError(f"не удалось прочитать '{path}': {exc}")
    try:
        return parse_test_repository(text)
    except RepositoryError as exc:
        raise RepositoryError(f"{path}: {exc}") from exc
