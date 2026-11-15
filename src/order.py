"""
Порядок загрузки зависимостей пакета.

Порядок строится обходом в глубину без рекурсии по готовому графу:
пакет попадает в список только после всех своих зависимостей, а
запрошенный пакет оказывается последним. Зависимости обходятся в том
порядке, в котором они записаны в индексе (сначала Pre-Depends, затем
Depends). Если в графе есть цикл, одно из его рёбер приходится
пропустить: ребро в пакет, который уже лежит на текущем пути обхода.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadOrder:
    """Порядок загрузки и рёбра, пропущенные из-за циклов.

    packages: пакеты в порядке загрузки, запрошенный пакет последний;
    skipped: пары (пакет, зависимость), которые не учитывались в порядке.
    """

    packages: tuple
    skipped: tuple


def build_load_order(graph):
    """Строит порядок загрузки по графу зависимостей."""
    packages = []
    skipped = []
    done = set()
    path = [graph.root]
    on_path = {graph.root}
    iterators = [iter(graph.edges[graph.root])]
    while iterators:
        child = next(iterators[-1], None)
        if child is None:
            node = path.pop()
            on_path.discard(node)
            done.add(node)
            packages.append(node)
            iterators.pop()
        elif child in on_path:
            skipped.append((path[-1], child))
        elif child not in done:
            path.append(child)
            on_path.add(child)
            iterators.append(iter(graph.edges[child]))
    return LoadOrder(tuple(packages), tuple(skipped))


def format_load_order(order, graph):
    """Формирует текстовое описание порядка загрузки для вывода."""
    lines = [f"Порядок загрузки зависимостей пакета {graph.root}:"]
    for number, name in enumerate(order.packages, 1):
        note = " [нет в репозитории]" if name in graph.unknown else ""
        lines.append(f"  {number}. {name}{note}")
    if order.skipped:
        lines.append(
            f"Рёбра, пропущенные из-за циклов ({len(order.skipped)}):"
        )
        lines.extend(f"  {node} -> {child}" for node, child in order.skipped)
    if graph.truncated:
        lines.append(
            f"Порядок неполный: зависимости {len(graph.truncated)} пакетов "
            "не раскрыты из-за ограничения глубины."
        )
    return "\n".join(lines)
