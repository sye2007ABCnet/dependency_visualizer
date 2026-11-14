"""Тесты этапа 3: таблица пакетов индекса и выбор версии."""

import unittest

from apt_repo import RepositoryError, build_package_table, select_stanza

TEXT = """Package: a
Version: 1.0

Package: b
Version: 2.0

Package: a
Version: 1.1
"""


class PackageTableTests(unittest.TestCase):
    """Группировка записей индекса по имени пакета."""

    def test_groups_versions_by_name(self):
        """Записи одного пакета собираются в список."""
        table = build_package_table(TEXT)
        self.assertEqual(list(table), ["a", "b"])
        versions = [stanza["Version"] for stanza in table["a"]]
        self.assertEqual(versions, ["1.0", "1.1"])

    def test_select_version(self):
        """Выбирается запись нужной версии."""
        stanzas = build_package_table(TEXT)["a"]
        self.assertEqual(select_stanza(stanzas, "a", "1.1")["Version"], "1.1")

    def test_select_missing_versions(self):
        """Нет версии — ошибка со списком доступных."""
        stanzas = build_package_table(TEXT)["a"]
        with self.assertRaisesRegex(RepositoryError, "1.0, 1.1"):
            select_stanza(stanzas, "a", "3.0")

    def test_select_from_nothing(self):
        """Нет записей — пакет не найден."""
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            select_stanza([], "zzz", "1.0")


if __name__ == "__main__":
    unittest.main()
