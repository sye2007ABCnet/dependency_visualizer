"""Тесты этапа 3: вывод графа зависимостей и коды завершения."""

import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from main import EXIT_CONFIG_ERROR, EXIT_DATA_ERROR, EXIT_OK, main
from repo_server import RepoServer

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def fixture(name):
    """Возвращает путь к файлу тестового репозитория."""
    return os.path.join(FIXTURE, name)


def run_main(argv):
    """Запускает main и возвращает (код, stdout, stderr)."""
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class AptModeTests(unittest.TestCase):
    """Режим с репозиторием Ubuntu: локальный сервер с настоящим индексом."""

    @classmethod
    def setUpClass(cls):
        """Запускает тестовый сервер один раз на все тесты класса."""
        cls.server = RepoServer().__enter__()

    @classmethod
    def tearDownClass(cls):
        """Останавливает тестовый сервер."""
        cls.server.__exit__(None, None, None)

    def run_package(self, package, version, *extra):
        """Запускает main для пакета из тестового репозитория."""
        argv = ["-p", package, "-r", self.server.base_url]
        return run_main(argv + ["--package-version", version, *extra])

    def test_transitive_graph(self):
        """Граф содержит зависимости зависимостей."""
        code, out, _ = self.run_package("curl", "7.81.0-1ubuntu1.30")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  curl -> libc6, libcurl4, zlib1g", out)
        self.assertIn("  libc6 (нет зависимостей)", out)

    def test_package_missing_from_index(self):
        """Пакет, которого нет в индексе, помечается."""
        _, out, _ = self.run_package("curl", "7.81.0-1ubuntu1.30")
        self.assertIn("  libcurl4 [нет в репозитории]", out)

    def test_pre_depends_come_first(self):
        """Pre-Depends входят в граф вместе с Depends."""
        _, out, _ = self.run_package("python3", "3.10.4-0ubuntu2")
        self.assertIn(
            "  python3 -> python3-minimal, python3.10, libpython3-stdlib",
            out,
        )

    def test_alternative_is_resolved(self):
        """Из группы альтернатив в граф попадает одна зависимость."""
        _, out, _ = self.run_package("debconf-utils", "1.5.79ubuntu1")
        self.assertIn("  debconf-utils -> debconf\n", out)

    def test_repeated_dependency_is_merged(self):
        """Пакет, указанный дважды (git-man), встречается один раз."""
        _, out, _ = self.run_package("git", "1:2.34.1-1ubuntu1")
        self.assertIn("  git -> libc6, libcurl3-gnutls, perl, git-man\n", out)

    def test_max_depth_option(self):
        """Опция -d ограничивает глубину графа."""
        _, out, _ = self.run_package("curl", "7.81.0-1ubuntu1.30", "-d", "1")
        self.assertIn("(максимальная глубина: 1)", out)
        self.assertIn("Пакетов в графе: 4", out)

    def test_load_order_for_apt_package(self):
        """Порядок загрузки выводится и для репозитория Ubuntu."""
        _, out, _ = self.run_package("curl", "7.81.0-1ubuntu1.30")
        self.assertIn(
            "  1. libc6\n  2. libcurl4 [нет в репозитории]\n"
            "  3. zlib1g [нет в репозитории]\n  4. curl",
            out,
        )

    def test_unknown_version(self):
        """Неизвестная версия — код 1 и список доступных версий."""
        code, _, err = self.run_package("curl", "1.0")
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("доступные версии", err)

    def test_unknown_package(self):
        """Неизвестный пакет — код 1."""
        code, _, err = self.run_package("nosuchpkg", "1.0")
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("не найден", err)


class TestModeTests(unittest.TestCase):
    """Тестовый режим: граф читается из файла, интернет не нужен."""

    def run_test_mode(self, name, *extra, package="A"):
        """Запускает main в тестовом режиме на файле из fixtures."""
        argv = ["-p", package, "-r", fixture(name), "-t"]
        return run_main(argv + list(extra))

    def test_diamond(self):
        """Общая зависимость D показана один раз."""
        code, out, _ = self.run_test_mode("simple.txt")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  A -> B, C\n  B -> D\n  D (нет зависимостей)", out)
        self.assertIn("Пакетов в графе: 4", out)
        self.assertIn("Циклических зависимостей не найдено.", out)

    def test_depth_limit(self):
        """Цепочка обрывается на заданной глубине."""
        _, out, _ = self.run_test_mode("chain.txt", "-d", "2")
        self.assertIn("  C [достигнута максимальная глубина]", out)
        self.assertNotIn("D", out.replace("Граф зависимостей", ""))

    def test_depth_larger_than_graph(self):
        """Достаточная глубина показывает всю цепочку."""
        _, out, _ = self.run_test_mode("chain.txt", "-d", "9")
        self.assertIn("  F (нет зависимостей)", out)
        self.assertNotIn("достигнута", out)

    def test_cycle(self):
        """Цикл найден и выведен, программа не зависает."""
        code, out, _ = self.run_test_mode("cycle.txt")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Циклические зависимости (1):", out)
        self.assertIn("  A -> B -> C -> A", out)

    def test_several_cycles(self):
        """Несколько циклов, включая самозависимость."""
        _, out, _ = self.run_test_mode("cycles.txt")
        self.assertIn("Циклические зависимости (3):", out)
        self.assertIn("  B -> C -> E -> B", out)
        self.assertIn("  D -> D", out)

    def test_cycle_hidden_by_depth(self):
        """Цикл глубже предела не показывается."""
        _, out, _ = self.run_test_mode("cycle.txt", "-d", "2")
        self.assertIn("Циклических зависимостей не найдено.", out)

    def test_shortcut_expands_node(self):
        """Вершина, достигнутая и глубоко, и близко, раскрыта полностью."""
        _, out, _ = self.run_test_mode("shortcut.txt", "-d", "3")
        self.assertIn("  X -> Y", out)

    def test_undeclared_dependency(self):
        """Неописанная зависимость помечается."""
        _, out, _ = self.run_test_mode("unknown.txt")
        self.assertIn("  X [нет в репозитории]", out)

    def test_other_root(self):
        """Корнем может быть любой пакет файла."""
        _, out, _ = self.run_test_mode("simple.txt", package="C")
        self.assertIn("Граф зависимостей пакета C", out)
        self.assertIn("Пакетов в графе: 2", out)

    def test_root_not_in_file(self):
        """Корня нет в файле — код 1."""
        code, _, err = self.run_test_mode("simple.txt", package="Z")
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("не найден в тестовом репозитории", err)

    def test_broken_file(self):
        """Файл с ошибкой формата — код 1 и номер строки."""
        handle, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(handle, "w", encoding="utf-8") as target:
            target.write("A: B\nбез двоеточия\n")
        code, _, err = run_main(["-p", "A", "-r", path, "-t"])
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("строка 2", err)

    def test_load_order_is_printed(self):
        """После графа выводится порядок загрузки: зависимости раньше."""
        _, out, _ = self.run_test_mode("layers.txt")
        self.assertIn(
            "Порядок загрузки зависимостей пакета A:\n"
            "  1. I\n  2. E\n  3. F\n  4. B\n  5. G\n"
            "  6. C\n  7. H\n  8. D\n  9. A",
            out,
        )

    def test_load_order_with_cycle(self):
        """Цикл не мешает порядку загрузки, пропущенное ребро указано."""
        _, out, _ = self.run_test_mode("cycle.txt")
        self.assertIn("  1. C\n  2. B\n  3. A", out)
        self.assertIn("Рёбра, пропущенные из-за циклов (1):\n  C -> A", out)

    def test_load_order_marks_unknown(self):
        """В порядке загрузки отсутствующий пакет помечен."""
        _, out, _ = self.run_test_mode("unknown.txt")
        self.assertIn("  2. X [нет в репозитории]", out)

    def test_load_order_is_incomplete_with_depth(self):
        """Ограничение глубины делает порядок неполным."""
        _, out, _ = self.run_test_mode("chain.txt", "-d", "2")
        self.assertIn("Порядок неполный", out)

    def test_config_error(self):
        """Ошибка параметров — код 2."""
        code, _, _ = run_main(["-p", "A", "-r", "/no/file.txt", "-t"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)


if __name__ == "__main__":
    unittest.main()
