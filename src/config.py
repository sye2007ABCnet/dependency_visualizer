"""
Конфигурация инструмента визуализации графа зависимостей.

Все параметры задаются опциями командной строки. Каждый параметр
проверяется отдельно, а найденные ошибки собираются вместе, чтобы
пользователь сразу увидел все проблемы, а не исправлял их по одной.
"""

import argparse
import os
import re
from dataclasses import dataclass, fields
from urllib.parse import urlparse

from dasbus import namespace

DEFAULT_OUTPUT = "graph.svg"
DEFAULT_MAX_DEPTH = 5
MIN_MAX_DEPTH = 1
IMAGE_EXTENSION = ".svg"
URL_SCHEMES = ("http", "https")

APT_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]+$")
TEST_PACKAGE_RE = re.compile(r"^[A-Z]+$")
APT_VERSION_RE = re.compile(r"^(\d+:)?[0-9][A-Za-z0-9.+~-]*$")


class ConfigError(Exception):
    """Ошибка конфигурации: сожержит список всех найденных проблем."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


@dataclass(frozen=True)
class Config:
    """Проверенные параметры запуска приложения."""

    package: str
    repo: str
    test_mode: bool
    version: str
    output: str
    ascii_tree: bool
    max_depth: int

    def as_key_value(self):
        """Возвращает все параметры в формате "ключ=значение"."""
        lines = []
        for field in fields(self):
            value = getattr(self, field.name)
            lines.append(f"{field.name}={'' if value is None else value}")
        return "\n".join(lines)


def _check_package(name, test_mode):
    """Проверяет имя пакета; формат зависит от режима работы."""
    if not name:
        return "имя пакета не может быть пустым"
    if test_mode and not TEST_PACKAGE_RE.match(name):
        return (f"имя пакета '{name}' недопустимо: в тестовом режиме "
                "пакеты называются большими латинскими буквами")
    if not test_mode and not APT_PACKAGE_RE.match(name):
        return (f"имя пакета '{name}' недопустимо: допускаются строчные "
                "латинские буквы, цифры и символы + - . "
                "(не короче 2 символов)")
    return None


def _check_repo(repo, test_mode):
    """Проверяет URL репозитория или путь к тестовому файлу."""
    if not repo:
        return "не задан URL репозитория или путь к файлу"
    if test_mode:
        if not os.path.isfile(repo):
            return f"файл тестового репозитория '{repo}' не найден"
        return None
    parsed = urlparse(repo)
    if parsed.scheme not in URL_SCHEMES or not parsed.netloc:
        return (f"'{repo}' не является URL-адресом "
                "(ожидается http:// или https://)")
    return None


def _check_version(version, test_mode):
    """Проверяет версию пакета (обязательна вне тестового режима)."""
    if version is None:
        if test_mode:
            return None
        return "версия пакета обязательна вне тестового режима"
    if not APT_VERSION_RE.match(version):
        return f"версия '{version}' имеет недопустимый формат"
    return None


def _check_output(output):
    """Проверяет имя файла для изображения графа."""
    if not output:
        return "имя файла не может быть пустым"
    if not output.lower().endswith(IMAGE_EXTENSION):
        return (f"файл изображения '{output}' должен иметь "
                f"расширение {IMAGE_EXTENSION}")
    directory = os.path.dirname(output) or "."
    if not os.path.isdir(directory):
        return f"каталог '{directory}' для файла изображения не существует"
    return None


def _parse_max_depth(raw):
    """Преобразует глубину в число. Возвращает (значение, ошибка)."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, f"максимальная глубина '{raw}' должна быть целым числом"
    if value < MIN_MAX_DEPTH:
        return None, (f"максимальная глубина должна быть "
                      f"не меньше {MIN_MAX_DEPTH}")
    return value, None


def build_config(namespace):
    """Проверяет все параметры и создаёт Config.

    Бросает ConfigError со списком всех найденных ошибок.
    """
    test_mode = namespace.test_mode
    max_depth, depth_error = _parse_max_depth(namespace.max_depth)
    checks = [
        _check_package(namespace.package, test_mode),
        _check_repo(namespace.repo, test_mode),
        _check_version(namespace.version, test_mode),
        _check_output(namespace.output),
        depth_error,
    ]
    errors = [error for error in checks if error]
    if errors:
        raise ConfigError(errors)
    return Config(
        package=namespace.package,
        repo=namespace.repo,
        test_mode=test_mode,
        version=namespace.version,
        output=namespace.output,
        ascii_tree=namespace.ascii_tree,
        max_depth=max_depth,
    )


class _ArgumentParser(argparse.ArgumentParser):
    """Парсер, сообщающий об ошибке через ConfigError."""

    def error(self, message):
        """Превращает ошибку разбора опций в ConfigError."""
        raise ConfigError([f"ошибка в опциях командной строки: {message}"])


def _create_parser():
    """Описывает все опции командной строки."""
    parser = _ArgumentParser(
        prog="main.py",
        description="Визуализация графа зависимостей пакетов Ubuntu.",
    )
    parser.add_argument("-p", "--package", required=True,
                        help="имя анализируемого пакета")
    parser.add_argument("-r", "--repo", required=True,
                        help="URL репозитория или путь к тестовому файлу")
    parser.add_argument("-t", "--test_mode", action="store_true",
                        help="режим работы с тестовым репозиторием")
    parser.add_argument("--package-version", dest="version", default=None,
                        help="версия пакета")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="имя файла с изображением графа (.svg)")
    parser.add_argument("-a", "--ascii_tree", action="store_true",
                        help="вывести зависимости в виде ASCII-дерева")
    parser.add_argument("-d", "--max_depth", default=str(DEFAULT_MAX_DEPTH),
                        help="максимальная глубина анализа зависимостей")
    return parser


def parse_args(argv=None):
    """Разбирает и проверяет опции командной строки, возвращает Config."""
    namespace = _create_parser().parse_args(argv)
    return build_config(namespace)
