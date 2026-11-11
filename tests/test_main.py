"""Тесты этапа 2: вывод прямых зависимостей и коды завершения."""

import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from main import EXIT_CONFIG_ERROR, EXIT_DATA_ERROR, EXIT_OK, main
from repo_server import RepoServer

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures",
                       "simple.txt")


def run_main(argv):
    """Запускает main и возвращает (код, stdout, stderr)."""
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class MainTests(unittest.TestCase):
    """Сквозные сценарии на локальном тестовом репозитории."""

    @classmethod
    def setUpClass(cls):
        """Запускает тестовый сервер один раз на все тесты класса."""
        cls.server = RepoServer().__enter__()

    @classmethod
    def tearDownClass(cls):
        """Останавливает тестовый сервер."""
        cls.server.__exit__(None, None, None)

    def run_package(self, package, version):
        """Запускает main для пакета из тестового репозитория."""
        return run_main(["-p", package, "-r", self.server.base_url,
                         "--package-version", version])

    def test_prints_direct_dependencies(self):
        """Выводятся прямые зависимости заданной версии."""
        code, out, _ = self.run_package("curl", "7.81.0-1ubuntu1.30")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("libcurl4 (= 7.81.0-1ubuntu1.30)", out)
        self.assertNotIn("(= 7.81.0-1)", out)

    def test_marks_pre_depends(self):
        """Зависимости из Pre-Depends помечаются отдельно."""
        _, out, _ = self.run_package("python3", "3.10.4-0ubuntu2")
        self.assertIn("python3-minimal (= 3.10.4-0ubuntu2) [Pre-Depends]",
                      out)

    def test_alternatives_shown(self):
        """Альтернативы выводятся через '|'."""
        _, out, _ = self.run_package("debconf-utils", "1.5.79ubuntu1")
        self.assertIn("debconf (>= 1.5.79ubuntu1) | debconf-2.0", out)

    def test_package_without_dependencies(self):
        """Для пакета без зависимостей выводится отдельное сообщение."""
        _, out, _ = self.run_package("libc6", "2.35-0ubuntu3")
        self.assertIn("нет прямых зависимостей", out)

    def test_unknown_version(self):
        """Неизвестная версия — код 1 и список доступных версий."""
        code, _, err = self.run_package("curl", "1.0")
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("доступные версии", err)

    def test_test_mode_not_yet_supported(self):
        """Тестовый режим на этом этапе ещё не поддерживается."""
        code, _, err = run_main(["-p", "A", "-r", FIXTURE, "-t"])
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("этапе 3", err)

    def test_config_error(self):
        """Ошибка параметров — код 2."""
        code, _, _ = run_main(["-p", "curl", "-r", "bad"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)


if __name__ == "__main__":
    unittest.main()
