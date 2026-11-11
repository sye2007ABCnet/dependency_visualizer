"""
Разбор полей зависимостей пакетов Ubuntu (apt).

Поле Depends содержит список групп через запятую. Группа может состоять
из нескольких альтернатив через '|': достаточно установить любую из
них. Каждая альтернатива — имя пакета, необязательный квалификатор
архитектуры (':any') и необязательное ограничение версии в скобках.
"""

import re
from dataclasses import dataclass

DEPENDENCY_FIELDS = ("Pre-Depends", "Depends")

_RELATION_RE = re.compile(
    r"^(?P<name>[a-z0-9][a-z0-9+.-]*)"
    r"(?::(?P<arch>[a-z0-9-]+))?\s*"
    r"(?:\(\s*(?P<op><<|<=|=|>=|>>)\s*(?P<version>[^)\s]+)\s*\))?\s*"
    r"(?:\[[^\]]*\])?\s*(?:<[^>]*>)?$"
)


class DependencyParseError(ValueError):
    """Строку зависимости не удалось разобрать."""


@dataclass(frozen=True)
class Dependency:
    """Одна альтернатива внутри группы зависимостей."""

    name: str
    operator: str = None
    version: str = None
    arch: str = None

    def __str__(self):
        """Возвращает зависимость в записи, принятой в apt."""
        text = self.name if self.arch is None else f"{self.name}:{self.arch}"
        if self.operator:
            text += f" ({self.operator} {self.version})"
        return text


@dataclass(frozen=True)
class DependencyGroup:
    """Группа альтернатив; field — поле, из которого она взята."""

    alternatives: tuple
    field: str

    def __str__(self):
        """Возвращает группу в виде 'a | b'."""
        return " | ".join(str(dep) for dep in self.alternatives)


def parse_relation(text):
    """Разбирает одну альтернативу, например 'libc6 (>= 2.34)'."""
    match = _RELATION_RE.match(text.strip())
    if match is None:
        raise DependencyParseError(f"не удалось разобрать '{text.strip()}'")
    return Dependency(
        name=match.group("name"),
        operator=match.group("op"),
        version=match.group("version"),
        arch=match.group("arch"),
    )


def parse_dependency_field(value, field="Depends"):
    """Разбирает значение поля зависимостей в список DependencyGroup."""
    groups = []
    for raw_group in value.split(","):
        if not raw_group.strip():
            continue
        alternatives = tuple(
            parse_relation(part) for part in raw_group.split("|")
        )
        groups.append(DependencyGroup(alternatives=alternatives, field=field))
    return groups


def direct_dependencies(stanza):
    """Возвращает прямые зависимости пакета из его записи в индексе.

    Учитываются поля Pre-Depends и Depends: оба обязательны для
    установки пакета.
    """
    groups = []
    for field in DEPENDENCY_FIELDS:
        value = stanza.get(field)
        if value:
            groups.extend(parse_dependency_field(value, field))
    return groups
