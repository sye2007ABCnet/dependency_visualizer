"""
Инструмент визуализации графа зависимостей пакетов Ubuntu (apt).

Этап 1: минимальный прототип с конфигурацией. Приложение разбирает
опции командной строки, проверяет их и выводит все параметры в
формате ключ=значение.
"""

import sys

from config import ConfigError, parse_args

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


def main(argv=None):
    """Точка входа. Возвращает код завершения процесса."""
    try:
        config = parse_args(argv)
    except ConfigError as exc:
        for error in exc.errors:
            print(f"ошибка: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    print(config.as_key_value())
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
