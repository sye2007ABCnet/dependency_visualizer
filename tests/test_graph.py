"""Тесты этапа 3: построение графа, глубина и циклические зависимости."""

import unittest

from graph import build_graph, find_cycles, format_graph

BIG_CHAIN_LENGTH = 5000
BIG_DEPTH = 10000


class DictSource:
    """Источник зависимостей на словаре: проверяем алгоритм без файлов."""

    def __init__(self, packages):
        """Запоминает словарь «пакет -> кортеж зависимостей»."""
        self.packages = packages

    def dependencies(self, name):
        """Возвращает зависимости пакета или None, если пакета нет."""
        return self._packages.get(name)


def graph_of(packages, max_depth, root="A"):
    """Строит граф для словаря пакетов."""
    return build_graph(root, DictSource(packages), max_depth)


class BuildGraphTests(unittest.TestCase):
    """Транзитивные зависимости и порядок обхода."""

    def test_transitive_dependencies(self):
        """В граф попадают зависимости зависимостей."""
        graph = graph_of({"A": ("B", "C"), "B": ("D",), "C": ("D",)}, 5)
        self.assertEqual(
            graph.edges,
            {"A": ("B", "C"), "B": ("D",), "D": (), "C": ("D",)}
        )

    def test_order_is_depth_first(self):
        """Вершины перечисляются в порядке обхода в глубину."""
        graph = graph_of({"A": ("B", "C"), "B": ("D",)}, 5)
        self.assertEqual(list(graph.edges), ["A", "B", "C", "D"])

    def test_unreachable_packages_are_ignored(self):
        """Пакеты, недостижимые из корня, в граф не попадают."""
        graph = graph_of({"A": ("B",), "B": (), "Z": ("A",)}, 5)
        self.assertNotIn("Z", graph.edges)

    def test_unknown_package(self):
        """Пакет, которого нет в репозитории, отмечается отдельно."""
        graph = graph_of({"A": ("B", "X"), "B": ()}, 5)
        self.assertEqual(graph.unknown, frozenset({"X"}))
        self.assertEqual(graph.edges["X"], ())

    def test_deep_chain_needs_no_recursion(self):
        """Цепочка длиннее лимита рекурсии Python строится без ошибок."""
        names = [f"P{i}" for i in range(BIG_CHAIN_LENGTH)]
        packages = {a: (b,) for a, b in zip(names, names[1:])}
        packages[names[-1]] = ()
        graph = graph_of(packages, BIG_DEPTH, root=names[0])
        self.assertEqual(len(graph.edges), BIG_CHAIN_LENGTH)
        self.assertEqual(graph.cycles, ())


class MaxDepthTests(unittest.TestCase):
    """Ограничение глубины анализа."""

    CHAIN = {"A": ("B",), "B": ("C",), "C": ("D",), "D": ()}

    def test_depth_one_gives_direct_dependencies(self):
        """Глубина 1: корень и его прямые зависимости."""
        graph = graph_of(self.CHAIN, 1)
        self.assertEqual(list(graph.edges), ["A", "B"])
        self.assertEqual(graph.truncated, frozenset({"B"}))

    def test_depth_limits_the_graph(self):
        """Вершины глубже предела в граф не попадают."""
        graph = graph_of(self.CHAIN, 2)
        self.assertEqual(list(graph.edges), ["A", "B", "C"])
        self.assertEqual(graph.edges["C"], ())
        self.assertEqual(graph.truncated, frozenset({"C"}))

    def test_depth_larger_than_graph(self):
        """Если глубина больше графа, обрезанных вершин нет."""
        graph = graph_of(self.CHAIN, 10)
        self.assertEqual(len(graph.edges), 4)
        self.assertEqual(graph.truncated, frozenset())

    def test_leaf_on_the_limit_is_not_truncated(self):
        """Вершина без зависимостей на границе глубины не обрезана."""
        graph = graph_of({"A": ("B",), "B": ()}, 1)
        self.assertEqual(graph.truncated, frozenset())

    def test_shorter_path_expands_node_again(self):
        """Вершина, достигнутая сначала глубоко, а потом близко, раскрыта."""
        packages = {
            "A": ("B", "X"),
            "B": ("C",),
            "C": ("X",),
            "X": ("Y",),
            "Y": (),
        }
        graph = graph_of(packages, 3)
        self.assertEqual(graph.edges["X"], ("Y",))
        self.assertEqual(graph.truncated, frozenset())


class CycleTests(unittest.TestCase):
    """Циклические зависимости."""

    def test_simple_cycle(self):
        """Простой цикл найден, обход завершается."""
        graph = graph_of({"A": ("B",), "B": ("C",), "C": ("A",)}, 5)
        self.assertEqual(graph.cycles, (("A", "B", "C", "A"),))
        self.assertEqual(len(graph.edges), 3)

    def test_self_dependency(self):
        """Зависимость пакета от самого себя — цикл из одной вершины."""
        graph = graph_of({"A": ("A", "B"), "B": ()}, 5)
        self.assertEqual(graph.cycles, (("A", "A"),))

    def test_several_cycles(self):
        """Несколько циклов в одном графе."""
        packages = {
            "A": ("B", "C"),
            "B": ("C", "D"),
            "C": ("A", "E"),
            "D": ("D", "F"),
            "E": ("B",),
            "F": (),
        }
        graph = graph_of(packages, 5)
        self.assertEqual(
            set(graph.cycles),
            {("A", "B", "C", "A"), ("B", "C", "E", "B"), ("D", "D")},
        )

    def test_cycle_beyond_is_not_reported(self):
        """Цикл, не уместившийся в глубину, в графе не виден."""
        graph = graph_of({"A": ("B",), "B": ("C",), "C": ("A",)}, 2)
        self.assertEqual(graph.cycles, ())
        self.assertEqual(graph.truncated, frozenset({"C"}))

    def test_cycle_through_root(self):
        """Цикл возвращается в корень."""
        graph = graph_of({"A": ("B",), "B": ("A",)}, 5)
        self.assertEqual(graph.cycles, (("A", "B", "A"),))

    def test_find_cycles_on_acyclic_graph(self):
        """В графе без циклов их нет."""
        edges = {"A": ("B", "C"), "B": ("C",), "C": ()}
        self.assertEqual(find_cycles("A", edges), ())


class FormatTests(unittest.TestCase):
    """Текстовое представление графа."""

    def test_all_markers(self):
        """Выводятся рёбра, пометки и сводка."""
        packages = {"A": ("B", "X", "C"), "B": ("A",), "C": ("D",)}
        text = format_graph(graph_of(packages, 1), 1)
        self.assertIn("(максимальная глубина: 1)", text)
        self.assertIn("  A -> B, X, C", text)
        self.assertIn("  B [достигнута максимальная глубина]", text)
        self.assertIn("  X [нет в репозитории]", text)
        self.assertIn("Пакетов в графе: 4", text)

    def test_cycles_listed(self):
        """Найденные циклы перечислены стрелками."""
        text = format_graph(graph_of({"A": ("B",), "B": ("A",)}, 5), 5)
        self.assertIn("Циклические зависимости (1):", text)
        self.assertIn("  A -> B -> A", text)

    def test_leaf_and_no_cycles(self):
        """Вершина без зависимостей и отсутствие циклов отмечены."""
        text = format_graph(graph_of({"A": ("B",), "B": ()}, 5), 5)
        self.assertIn("  B (нет зависимостей)", text)
        self.assertIn("Циклических зависимостей не найдено.", text)


if __name__ == "__main__":
    unittest.main()
