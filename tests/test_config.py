"""Тесты этапов 1-2: разбор и проверка параметров командной строки."""

import os
import unittest

from config import ConfigError, parse_args

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures",
                       "simple.txt")
REAL_ARGS = ["-p", "curl", "-r", "http://archive.ubuntu.com/ubuntu",
             "--package-version", "7.81.0-1"]


class ValidConfigTests(unittest.TestCase):
    """Корректные наборы параметров."""

    def test_real_repository_mode(self):
        """Обычный режим: пакет apt, URL и версия."""
        config = parse_args(REAL_ARGS)
        self.assertEqual(config.package, "curl")
        self.assertFalse(config.test_mode)
        self.assertEqual(config.max_depth, 5)

    def test_test_mode_without_version(self):
        """В тестовом режиме версия необязательна."""
        config = parse_args(["-p", "A", "-r", FIXTURE, "-t"])
        self.assertTrue(config.test_mode)
        self.assertIsNone(config.version)

    def test_all_options(self):
        """Все опции задаются одновременно."""
        config = parse_args(REAL_ARGS + ["-o", "out.svg", "-a", "-d", "3"])
        self.assertEqual(config.output, "out.svg")
        self.assertTrue(config.ascii_tree)
        self.assertEqual(config.max_depth, 3)


class InvalidConfigTests(unittest.TestCase):
    """Обработка ошибок для каждого параметра."""

    def assert_error(self, argv, fragment):
        """Проверяет, что разбор argv даёт ошибку с нужным текстом."""
        with self.assertRaises(ConfigError) as ctx:
            parse_args(argv)
        self.assertIn(fragment, str(ctx.exception))

    def test_missing_required_option(self):
        """Отсутствие обязательной опции -p."""
        self.assert_error(["-r", "http://x.org"], "опциях")

    def test_bad_package_name(self):
        """Недопустимое имя пакета apt."""
        argv = ["-p", "Bad_Name", "-r", "http://x.org",
                "--package-version", "1.0"]
        self.assert_error(argv, "имя пакета")

    def test_lowercase_name_in_test_mode(self):
        """В тестовом режиме имя должно состоять из больших букв."""
        self.assert_error(["-p", "a", "-r", FIXTURE, "-t"], "большими")

    def test_bad_url(self):
        """Строка, не являющаяся URL."""
        argv = ["-p", "curl", "-r", "archive", "--package-version", "1.0"]
        self.assert_error(argv, "URL")

    def test_missing_test_file(self):
        """Несуществующий файл тестового репозитория."""
        self.assert_error(["-p", "A", "-r", "/no/file.txt", "-t"],
                          "не найден")

    def test_version_required(self):
        """Вне тестового режима версия обязательна."""
        self.assert_error(["-p", "curl", "-r", "http://x.org"], "версия")

    def test_bad_version(self):
        """Недопустимый формат версии."""
        self.assert_error(REAL_ARGS[:4] + ["--package-version", "abc"],
                          "формат")

    def test_bad_output_extension(self):
        """Файл изображения должен иметь расширение .svg."""
        self.assert_error(REAL_ARGS + ["-o", "graph.png"], ".svg")

    def test_missing_output_directory(self):
        """Каталог для файла изображения должен существовать."""
        self.assert_error(REAL_ARGS + ["-o", "/no/dir/g.svg"], "каталог")

    def test_depth_not_number(self):
        """Глубина должна быть целым числом."""
        self.assert_error(REAL_ARGS + ["-d", "abc"], "целым")

    def test_depth_too_small(self):
        """Глубина должна быть не меньше 1."""
        self.assert_error(REAL_ARGS + ["-d", "0"], "не меньше")

    def test_all_errors_reported_together(self):
        """Несколько ошибок сообщаются одновременно."""
        argv = ["-p", "Bad_Name", "-r", "archive", "-d", "0"]
        with self.assertRaises(ConfigError) as ctx:
            parse_args(argv)
        self.assertGreaterEqual(len(ctx.exception.errors), 3)


if __name__ == "__main__":
    unittest.main()
