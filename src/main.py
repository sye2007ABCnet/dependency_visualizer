"""
Инструмент визуализации графа зависимостей пакетов Ubuntu (apt).

Этап 2: сбор данных. Приложение скачивает индекс пакетов репозитория,
находит заданную версию пакета и выводит его прямые зависимости.
"""

import sys

from apt_repo import RepositoryError, build_index_url, fetch_index
from apt_repo import find_package
from config import ConfigError, parse_args
from dependencies import DependencyParseError, direct_dependencies

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2


def collect_direct_dependencies(config):
    """Скачивает индекс и возвращает прямые зависимости пакета."""
    if config.test_mode:
        raise RepositoryError(
            "работа с тестовым репозиторием появится на этапе 3")
    index_url = build_index_url(config.repo)
    print(f"Загрузка индекса: {index_url}", file=sys.stderr)
    stanza = find_package(fetch_index(index_url), config.package,
                          config.version)
    return direct_dependencies(stanza)


def format_dependencies(package, version, groups):
    """Формирует текст со списком прямых зависимостей."""
    if not groups:
        return f"У пакета {package} {version} нет прямых зависимостей."
    lines = [f"Прямые зависимости пакета {package} {version}:"]
    for group in groups:
        suffix = " [Pre-Depends]" if group.field == "Pre-Depends" else ""
        lines.append(f"  {group}{suffix}")
    return "\n".join(lines)


def main(argv=None):
    """Точка входа. Возвращает код завершения процесса."""
    try:
        config = parse_args(argv)
    except ConfigError as exc:
        for error in exc.errors:
            print(f"ошибка: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        groups = collect_direct_dependencies(config)
    except (RepositoryError, DependencyParseError) as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return EXIT_DATA_ERROR
    print(format_dependencies(config.package, config.version, groups))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
