"""
Инструмент визуализации графа зависимостей пакетов Ubuntu (apt).

Этап 3: основные операции. Приложение строит граф зависимостей пакета
с учётом транзитивности обходом в глубину без рекурсии и выводит его.
Учитываются максимальная глубина анализа и циклические зависимости.
В тестовом режиме граф читается из текстового файла.
"""

import sys

from apt_repo import RepositoryError, build_index_url, fetch_index
from config import ConfigError, parse_args
from dependencies import DependencyParseError
from graph import build_graph, format_graph
from sources import AptSource, FileSource, load_test_repository

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2


def open_source(config):
    """Открывает источник зависимостей в выбранном режиме работы."""
    if config.test_mode:
        packages = load_test_repository(config.repo)
        return FileSource(packages, config.package)
    index_url = build_index_url(config.repo)
    print(f"Загрузка индекса: {index_url}", file=sys.stderr)
    return AptSource(fetch_index(index_url), config.package, config.version)


def main(argv=None):
    """Точка входа. Возвращает код завершения процесса."""
    try:
        config = parse_args(argv)
    except ConfigError as exc:
        for error in exc.errors:
            print(f"ошибка: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        source = open_source(config)
        graph = build_graph(config.package, source, config.max_depth)
    except (RepositoryError, DependencyParseError) as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return EXIT_DATA_ERROR
    print(format_graph(graph, config.max_depth))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
