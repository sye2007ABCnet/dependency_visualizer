"""Тесты этапа 3: источники данных (тестовый репозиторий и индекс apt)."""

import os
import tempfile
import unittest

from apt_repo import RepositoryError
from graph import build_graph
from sources import (
    AptSource,
    FileSource,
    load_test_repository,
    parse_test_repository,
)

INDEX = """Package: app
Version: 1.0
Pre-Depends: base (>= 1.0)
Depends: base, lib-a | lib-b, virtual-x | lib-b, ghost | phantom

Package: app
Version: 2.0
Depends: other

Package: base
Version: 1.0
Depends: app

Package: lib-b
Version: 1.0
"""


class ParseTestRepositoryTests(unittest.TestCase):
    """Разбор текстового описания тестового репозитория."""

    def test_valid_description(self):
        """Пустые строки и комментарии пропускаются."""
        text = "# граф\nA: B C\n\nB:\nC: B\n"
        self.assertEqual(
            parse_test_repository(text),
            {"A": ("B", "C"), "B": (), "C": ("B",)},
        )

    def test_duplicate_dependencies_are_merged(self):
        """Повторы в списке зависимостей убираются."""
        self.assertEqual(parse_test_repository("A: B B\n"), {"A": ("B",)})

    def assert_error(self, text, fragment):
        """Проверяет, что разбор падает с ошибкой, содержащей fragment."""
        with self.assertRaises(RepositoryError) as caught:
            parse_test_repository(text)
        self.assertIn(fragment, str(caught.exception))

    def test_line_without_colon(self):
        """Строка без двоеточия — ошибка с номером строки."""
        self.assert_error("A: B\nC D\n", "строка 2")

    def test_lowercase_package_name(self):
        """Имя пакета маленькими буквами недопустимо."""
        self.assert_error("a: B\n", "имя 'a' недопустимо")

    def test_bad_dependency_name(self):
        """Недопустимое имя зависимости."""
        self.assert_error("A: B c\n", "имя 'c' недопустимо")

    def test_empty_package_name(self):
        """Пустое имя пакета недопустимо."""
        self.assert_error(": B\n", "недопустимо")

    def test_duplicate_package(self):
        """Повторное описание пакета — ошибка."""
        self.assert_error("A: B\nA: C\n", "описан повторно")


class LoadTestRepositoryTests(unittest.TestCase):
    """Чтение файла тестового репозитория."""

    def write(self, data):
        """Создаёт временный файл с данными и возвращает его путь."""
        handle, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(handle, "wb") as target:
            target.write(data)
        return path

    def test_load(self):
        """Файл читается в словарь пакетов."""
        path = self.write("A: B\n".encode("utf-8"))
        self.assertEqual(load_test_repository(path), {"A": ("B",)})

    def test_missing_file(self):
        """Отсутствующий файл — RepositoryError."""
        with self.assertRaises(RepositoryError):
            load_test_repository("/no/such/file.txt")

    def test_not_utf8(self):
        """Файл не в UTF-8 — RepositoryError."""
        with self.assertRaises(RepositoryError):
            load_test_repository(self.write(b"\xff\xfe\x00"))

    def test_error_mentions_file_name(self):
        """Ошибка разбора содержит путь к файлу."""
        path = self.write(b"oops\n")
        with self.assertRaises(RepositoryError) as caught:
            load_test_repository(path)
        self.assertIn(path, str(caught.exception))


class FileSourceTests(unittest.TestCase):
    """Источник на основе тестового репозитория."""

    def test_root_must_exist(self):
        """Корневой пакет должен быть описан в файле."""
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            FileSource({"A": ()}, "Z")

    def test_unknown_package_is_none(self):
        """Неописанный пакет — None, описанный — кортеж."""
        source = FileSource({"A": ("B",)}, "A")
        self.assertEqual(source.dependencies("A"), ("B",))
        self.assertIsNone(source.dependencies("B"))


class AptSourceTests(unittest.TestCase):
    """Источник на основе индекса пакетов Ubuntu."""

    def setUp(self):
        """Создаёт источник для корня app версии 1.0."""
        self.source = AptSource(INDEX, "app", "1.0")

    def test_dependencies_of_root(self):
        """Зависимости берутся у заданной версии, без повторов."""
        self.assertEqual(
            self.source.dependencies("app"), ("base", "lib-b", "ghost")
        )

    def test_other_version_of_root(self):
        """Для другой версии корня берутся её зависимости."""
        source = AptSource(INDEX, "app", "2.0")
        self.assertEqual(source.dependencies("app"), ("other",))

    def test_alternative_present_in_index_wins(self):
        """Из группы альтернатив выбирается первая, что есть в индексе."""
        self.assertIn("lib-b", self.source.dependencies("app"))
        self.assertNotIn("lib-a", self.source.dependencies("app"))

    def test_alternative_absent_everywhere(self):
        """Если нет ни одной альтернативы, берётся первая по списку."""
        self.assertIn("ghost", self.source.dependencies("app"))
        self.assertNotIn("phantom", self.source.dependencies("app"))

    def test_unknown_package_is_none(self):
        """Пакета нет в индексе — None."""
        self.assertIsNone(self.source.dependencies("ghost"))

    def test_package_without_dependencies(self):
        """Пакет без полей зависимостей — пустой кортеж."""
        self.assertEqual(self.source.dependencies("lib-b"), ())

    def test_missing_version(self):
        """Нет нужной версии корня — ошибка со списком версий."""
        with self.assertRaisesRegex(RepositoryError, "доступные версии"):
            AptSource(INDEX, "app", "9.9")

    def test_missing_root(self):
        """Нет корневого пакета — ошибка."""
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            AptSource(INDEX, "nothing", "1.0")

    def test_graph_with_cycle_through_root(self):
        """Цикл app -> base -> app находится в графе из индекса."""
        graph = build_graph("app", self.source, 5)
        self.assertEqual(graph.cycles, (("app", "base", "app"),))
        self.assertEqual(graph.unknown, frozenset({"ghost"}))


if __name__ == "__main__":
    unittest.main()
