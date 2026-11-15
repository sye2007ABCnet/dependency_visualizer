"""Тесты этапа 4: порядок загрузки зависимостей."""

import unittest

from graph import build_graph
from order import build_load_order, format_load_order

BIG_CHAIN_LENGTH = 5000
BIG_DEPTH = 10000


class DictSource:
    """Источник зависимостей на словаре: проверяем алгоритм без файлов."""

    def __init__(self, packages):
        """Запоминает словарь «пакет -> кортеж зависимостей»."""
        self._packages = packages

    def dependencies(self, name):
        """Возвращает зависимости пакета или None, если пакета нет."""
        return self._packages.get(name)


def order_of(packages, max_depth=BIG_DEPTH):
    """Возвращает (граф, порядок загрузки) для пакета A."""
    graph = build_graph("A", DictSource(packages), max_depth)
    return graph, build_load_order(graph)


class LoadOrderTests(unittest.TestCase):
    """Правильность порядка: зависимости идут раньше зависимых."""

    DIAMOND = {"A": ("B", "C"), "B": ("D",), "C": ("D",), "D": ()}

    def assert_dependencies_first(self, graph, order):
        """Проверяет, что каждая зависимость загружена до зависимого."""
        position = {name: i for i, name in enumerate(order.packages)}
        for node, children in graph.edges.items():
            for child in children:
                if (node, child) not in order.skipped:
                    self.assertLess(position[child], position[node])

    def test_diamond(self):
        """Общая зависимость загружается один раз и первой."""
        _, order = order_of(self.DIAMOND)
        self.assertEqual(order.packages, ("D", "B", "C", "A"))
        self.assertEqual(order.skipped, ())

    def test_requested_package_is_last(self):
        """Запрошенный пакет загружается последним."""
        _, order = order_of(self.DIAMOND)
        self.assertEqual(order.packages[-1], "A")

    def test_chain(self):
        """Цепочка загружается с конца."""
        chain = {"A": ("B",), "B": ("C",), "C": ()}
        _, order = order_of(chain)
        self.assertEqual(order.packages, ("C", "B", "A"))

    def test_layers(self):
        """В слоистом графе зависимости всегда раньше зависимых."""
        layers = {
            "A": ("B", "C", "D"),
            "B": ("E", "F"),
            "C": ("F", "G"),
            "D": ("G", "H"),
            "E": ("I",),
            "F": ("I",),
            "G": ("I",),
            "H": (),
            "I": (),
        }
        graph, order = order_of(layers)
        self.assertEqual(order.packages, tuple("IEFBGCHDA"))
        self.assert_dependencies_first(graph, order)

    def test_every_package_once(self):
        """Каждый пакет графа присутствует в порядке ровно один раз."""
        graph, order = order_of(self.DIAMOND)
        self.assertEqual(len(order.packages), len(set(order.packages)))
        self.assertEqual(set(order.packages), set(graph.edges))

    def test_single_package(self):
        """Пакет без зависимостей загружается один."""
        _, order = order_of({"A": ()})
        self.assertEqual(order.packages, ("A",))

    def test_deep_chain_needs_no_recursion(self):
        """Цепочка длиннее лимита рекурсии Python обрабатывается."""
        names = ["A"] + [f"P{i}" for i in range(BIG_CHAIN_LENGTH)]
        packages = {a: (b,) for a, b in zip(names, names[1:])}
        packages[names[-1]] = tuple()
        _, order = order_of(packages)
        self.assertEqual(len(order.packages), len(names))
        self.assertEqual(order.packages[0], names[-1])


class CycleOrderTests(unittest.TestCase):
    """Порядок при циклических зависимостях."""

    def test_simple_cycle(self):
        """Цикл разрывается ребром, ведущим назад по пути обхода."""
        graph, order = order_of({"A": ("B",), "B": ("C",), "C": ("A",)})
        self.assertEqual(order.packages, ("C", "B", "A"))
        self.assertEqual(order.skipped, (("C", "A"),))
        self.assertEqual(set(order.packages), set(graph.edges))

    def test_self_dependency(self):
        """Зависимость от самого себя пропускается."""
        _, order = order_of({"A": ("A", "B"), "B": ()})
        self.assertEqual(order.packages, ("B", "A"))
        self.assertEqual(order.skipped, (("A", "A"),))

    def test_several_cycles(self):
        """Все пакеты графа с циклами попадают в порядок один раз."""
        packages = {
            "A": ("B", "C"),
            "B": ("C", "D"),
            "C": ("A", "E"),
            "D": ("D", "F"),
            "E": ("B",),
            "F": (),
        }
        graph, order = order_of(packages)
        self.assertEqual(set(order.packages), set(graph.edges))
        self.assertEqual(len(order.packages), len(graph.edges))
        self.assertEqual(order.packages[-1], "A")


class FormatLoadOrderTests(unittest.TestCase):
    """Текстовое представление порядка загрузки."""

    def test_numbered_list(self):
        """Пакеты выводятся пронумерованным списком."""
        graph, order = order_of({"A": ("B",), "B": ()})
        self.assertEqual(
            format_load_order(order, graph),
            "Порядок загрузки зависимостей пакета A:\n  1. B\n  2. A",
        )

    def test_unknown_package_is_marked(self):
        """Пакет, которого нет в репозитории, помечается."""
        graph, order = order_of({"A": ("X",)})
        text = format_load_order(order, graph)
        self.assertIn("  1. X [нет в репозитории]", text)

    def test_skipped_edges_are_listed(self):
        """Пропущенные из-за цикла рёбра перечисляются."""
        graph, order = order_of({"A": ("B",), "B": ("A",)})
        text = format_load_order(order, graph)
        self.assertIn("Рёбра, пропущенные из-за циклов (1):", text)
        self.assertIn("  B -> A", text)

    def test_incomplete_order_warning(self):
        """При ограничении глубины выводится предупреждение."""
        graph, order = order_of({"A": ("B",), "B": ("C",), "C": ()}, 1)
        text = format_load_order(order, graph)
        self.assertIn("Порядок неполный: зависимости 1 пакетов", text)

    def test_complete_order_has_no_warning(self):
        """Если глубины хватило, предупреждения нет."""
        graph, order = order_of({"A": ("B",), "B": ()})
        self.assertNotIn("неполный", format_load_order(order, graph))


if __name__ == "__main__":
    unittest.main()
