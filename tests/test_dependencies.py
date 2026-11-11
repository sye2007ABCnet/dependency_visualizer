"""Тесты этапа 2: разбор полей зависимостей apt."""

import unittest

from dependencies import (Dependency, DependencyParseError,
                          direct_dependencies, parse_dependency_field,
                          parse_relation)


class ParseRelationTests(unittest.TestCase):
    """Разбор одной альтернативы."""

    def test_name_only(self):
        """Зависимость без ограничения версии."""
        self.assertEqual(parse_relation("perl"), Dependency("perl"))

    def test_version_constraint(self):
        """Оператор и версия в скобках."""
        dep = parse_relation("libc6 (>= 2.34)")
        self.assertEqual((dep.name, dep.operator, dep.version),
                         ("libc6", ">=", "2.34"))

    def test_epoch_in_version(self):
        """Версия с эпохой (число и двоеточие в начале)."""
        dep = parse_relation("zlib1g (>= 1:1.1.4)")
        self.assertEqual(dep.version, "1:1.1.4")

    def test_strict_operators(self):
        """Операторы << и >> распознаются целиком."""
        self.assertEqual(parse_relation("git-man (<< 1:2.34.1-.)").operator,
                         "<<")
        self.assertEqual(parse_relation("git-man (>> 1:2.34.1)").operator,
                         ">>")

    def test_arch_qualifier(self):
        """Квалификатор архитектуры отделяется от имени."""
        dep = parse_relation("python3:any")
        self.assertEqual((dep.name, dep.arch), ("python3", "any"))
        self.assertEqual(str(dep), "python3:any")

    def test_invalid_relation(self):
        """Некорректная запись вызывает DependencyParseError."""
        with self.assertRaises(DependencyParseError):
            parse_relation("libc6 (>= 2.34")


class ParseFieldTests(unittest.TestCase):
    """Разбор поля целиком."""

    def test_groups_split_by_comma(self):
        """Группы разделяются запятыми."""
        groups = parse_dependency_field("libc6 (>= 2.34), perl")
        self.assertEqual([str(g) for g in groups],
                         ["libc6 (>= 2.34)", "perl"])

    def test_alternatives(self):
        """Альтернативы внутри группы разделяются '|'."""
        groups = parse_dependency_field("debconf (>= 0.5) | debconf-2.0")
        self.assertEqual(len(groups), 1)
        self.assertEqual([d.name for d in groups[0].alternatives],
                         ["debconf", "debconf-2.0"])

    def test_empty_field(self):
        """Пустое поле не даёт зависимостей."""
        self.assertEqual(parse_dependency_field(""), [])

    def test_direct_dependencies_both_fields(self):
        """Учитываются и Pre-Depends, и Depends."""
        stanza = {"Pre-Depends": "python3-minimal", "Depends": "python3.10"}
        groups = direct_dependencies(stanza)
        self.assertEqual([(str(g), g.field) for g in groups],
                         [("python3-minimal", "Pre-Depends"),
                          ("python3.10", "Depends")])

    def test_no_dependencies(self):
        """Пакет без полей зависимостей."""
        self.assertEqual(direct_dependencies({"Package": "libc6"}), [])


if __name__ == "__main__":
    unittest.main()
