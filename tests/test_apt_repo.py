"""Тесты этапа 2: загрузка и разбор индекса пакетов."""

import unittest

from apt_repo import (RepositoryError, build_index_url, fetch_index,
                      find_package, iter_stanzas)
from repo_server import INDEX_DIR, RepoServer

SAMPLE = """Package: a
Version: 1.0
Description: first line
 continuation

Package: b
Version: 2.0
"""


class BuildIndexUrlTests(unittest.TestCase):
    """Определение URL индекса по URL репозитория."""

    def test_archive_root(self):
        """К корню архива добавляется путь по умолчанию."""
        url = build_index_url("http://archive.ubuntu.com/ubuntu/")
        self.assertEqual(url, "http://archive.ubuntu.com/ubuntu/dists/"
                              "jammy/main/binary-amd64/Packages.gz")

    def test_direct_index_url(self):
        """URL файла Packages.xz используется без изменений."""
        url = "http://x.org/dists/noble/main/binary-amd64/Packages.xz"
        self.assertEqual(build_index_url(url), url)


class StanzaTests(unittest.TestCase):
    """Разбор записей индекса."""

    def test_records_split_by_blank_line(self):
        """Записи разделяются пустой строкой."""
        names = [s["Package"] for s in iter_stanzas(SAMPLE)]
        self.assertEqual(names, ["a", "b"])

    def test_continuation_line(self):
        """Строка с отступом продолжает предыдущее поле."""
        first = next(iter_stanzas(SAMPLE))
        self.assertEqual(first["Description"], "first line\ncontinuation")

    def test_find_package(self):
        """Поиск записи по имени и версии."""
        self.assertEqual(find_package(SAMPLE, "b", "2.0")["Package"], "b")

    def test_missing_package(self):
        """Отсутствующий пакет — ошибка."""
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            find_package(SAMPLE, "zzz", "1.0")

    def test_missing_version_lists_available(self):
        """Отсутствующая версия — ошибка со списком доступных версий."""
        with self.assertRaisesRegex(RepositoryError, "доступные версии: 1.0"):
            find_package(SAMPLE, "a", "9.9")


class FetchIndexTests(unittest.TestCase):
    """Загрузка индекса по HTTP с локального тестового сервера."""

    @classmethod
    def setUpClass(cls):
        """Запускает тестовый сервер один раз на все тесты класса."""
        cls.server = RepoServer().__enter__()

    @classmethod
    def tearDownClass(cls):
        """Останавливает тестовый сервер."""
        cls.server.__exit__(None, None, None)

    def url(self, name):
        """URL файла индекса на тестовом сервере."""
        return f"{self.server.base_url}/{INDEX_DIR}/{name}"

    def test_plain_gz_and_xz_are_equal(self):
        """Несжатый, .gz и .xz индексы дают одинаковый текст."""
        texts = {fetch_index(self.url(name))
                 for name in ("Packages", "Packages.gz", "Packages.xz")}
        self.assertEqual(len(texts), 1)
        self.assertIn("Package: curl", texts.pop())

    def test_http_error(self):
        """Ответ 404 превращается в RepositoryError."""
        with self.assertRaisesRegex(RepositoryError, "404"):
            fetch_index(self.url("Missing.gz"))

    def test_broken_archive(self):
        """Повреждённый архив — RepositoryError."""
        with self.assertRaisesRegex(RepositoryError, "распаковать"):
            fetch_index(f"{self.server.base_url}/broken/Packages.gz")

    def test_connection_refused(self):
        """Недоступный сервер — RepositoryError."""
        with self.assertRaisesRegex(RepositoryError, "подключиться"):
            fetch_index("http://127.0.0.1:9/Packages")


if __name__ == "__main__":
    unittest.main()
