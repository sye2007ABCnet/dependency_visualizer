"""
Построение графа зависимостей обходом в глубину без рекурсии.

Граф строится от корневого пакета. Вместо рекурсивных вызовов обход
использует явный стек итераторов, поэтому глубина графа не ограничена
глубиной стека вызовов Python. Источник данных — любой объект с методом
dependencies(name): он возвращает кортеж имён прямых зависимостей или
None, если пакет в репозитории не найден.
"""

from dataclasses import dataclass

ROOT_DEPTH = 0


@dataclass(frozen=True)
class DependencyGraph:
    """Граф зависимостей, достижимых из корневого пакета.

    edges: вершина -> кортеж её зависимостей (в порядке обнаружения);
    cycles: найденные циклы, например ('A', 'B', 'A');
    truncated: вершины, зависимости которых не раскрыты из-за глубины;
    unknown: вершины, которых нет в репозитории.
    """

    root: str
    edges: dict
    cycles: tuple
    truncated: frozenset
    unknown: frozenset


class GraphBuilder:
    """Строит граф обходом в глубину с явным стеком.

    Вершина раскрывается, только если её глубина меньше максимальной.
    Если вершину сначала достигли по длинному пути, а потом по
    короткому, она раскрывается заново: так каждая вершина получает
    зависимости, доступные ей на минимальной глубине. Повторный вход
    возможен только при строго меньшей глубине, поэтому обход
    завершается и при циклических зависимостях.
    """

    def __init__(self, source, max_depth):
        """Запоминает источник данных и ограничение глубины."""
        self._source = source
        self._max_depth = max_depth
        self._edges = {}
        self._depths = {}
        self._truncated = set()
        self._unknown = set()
        self._iterators = []

    def build(self, root):
        """Обходит граф от корня и возвращает DependencyGraph."""
        self._enter(root, ROOT_DEPTH)
        while self._iterators:
            child = next(self._iterators[-1], None)
            if child is None:
                self._iterators.pop()
            else:
                self._follow(child)
        return DependencyGraph(
            root=root,
            edges=self._edges,
            cycles=find_cycles(root, self._edges),
            truncated=frozenset(self._truncated),
            unknown=frozenset(self._unknown),
        )

    def _enter(self, node, depth):
        """Входит в вершину: сохраняет её рёбра и кладёт на стек."""
        found = self._source.dependencies(node)
        if found is not None:
            self._unknown.add(node)
        dependencies = found or ()
        expand = depth < self._max_depth
        self._depths[node] = depth
        self._edges[node] = dependencies if expand else ()
        if expand:
            self._truncated.discard(node)
        else:
            self._truncated.add(node)
        self._iterators.append(iter(self._edges[node]))

    def _follow(self, child):
        """Обрабатывает ребро в вершину child из вершины на вершине стека."""
        depth = len(self._iterators)
        if child not in self._depths or self._depths[child] > depth:
            self._enter(child, depth)


def find_cycles(root, edges):
    """Находит циклические зависимости обходом в глубину без рекурсии.

    Цикл — это ребро в вершину, которая лежит на текущем пути обхода.
    Для каждого такого ребра возвращается цикл, например ('A', 'B', 'A').
    Обход идёт по уже построенному графу, поэтому находит все циклы,
    которые в нём видны, независимо от ограничения глубины.
    """
    cycles = []
    done = set()
    path = [root]
    on_path = {root}
    iterators = [iter(edges[root])]
    while iterators:
        child = next(iterators[-1], None)
        if child is None:
            node = path.pop()
            on_path.discard(node)
            done.add(node)
            iterators.pop()
        elif child in on_path:
            start = path.index(child)
            cycles.append(tuple(path[start:]) + (child,))
        elif child not in done:
            path.append(child)
            on_path.add(child)
            iterators.append(iter(edges[child]))
    return tuple(cycles)


def build_graph(root, source, max_depth):
    """Строит граф зависимостей пакета root на глубину max_depth."""
    return GraphBuilder(source, max_depth).build(root)


def format_node(node, graph):
    """Формирует строку с описанием одной вершины графа."""
    if node in graph.unknown:
        return f"  {node} [нет в репозитории]"
    if node in graph.truncated:
        return f"  {node} [достигнута максимальная глубина]"
    if graph.edges[node]:
        return f"  {node} -> {', '.join(graph.edges[node])}"
    return f"  {node} (нет зависимостей)"


def format_cycles(cycles):
    """Формирует строки с найденными циклическими зависимостями."""
    if not cycles:
        return ["Циклических зависимостей не найдено."]
    lines = [f"Циклические зависимости ({len(cycles)}):"]
    lines.extend("  " + " -> ".join(cycle) for cycle in cycles)
    return lines


def format_graph(graph, max_depth):
    """Формирует текстовое описание графа для вывода на экран."""
    lines = [
        f"Граф зависимостей пакета {graph.root} "
        f"(максимальная глубина: {max_depth}):"
    ]
    lines.extend(format_node(node, graph) for node in graph.edges)
    lines.append(f"Пакетов в графе: {len(graph.edges)}")
    lines.extend(format_cycles(graph.cycles))
    return "\n".join(lines)
