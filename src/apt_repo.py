"""
Получение данных о пакетах из репозитория Ubuntu (apt).

Индекс пакетов репозитория — файл Packages (часто сжатый в .gz или .xz).
Он состоит из записей, разделённых пустыми строками; каждая запись —
набор полей 'Имя: значение'. Строки, начинающиеся с пробела, продолжают
значение предыдущего поля. Файл скачивается и разбирается средствами
стандартной библиотеки, без менеджеров пакетов.
"""

import gzip
import lzma
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULT_SUITE = "jammy"
DEFAULT_COMPONENT = "main"
DEFAULT_ARCH = "amd64"
INDEX_NAMES = ("Packages", "Packages.gz", "Packages.xz")
REQUEST_TIMEOUT = 60
USER_AGENT = "dependency-visualizer/0.2"
CONTINUATION_CHARS = (" ", "\t")


class RepositoryError(Exception):
    """Ошибка получения или разбора данных репозитория."""


def build_index_url(repo_url):
    """Возвращает URL индекса пакетов.

    Если repo_url уже указывает на файл Packages, Packages.gz или
    Packages.xz, он используется как есть. Иначе он считается корнем
    архива, и к нему добавляется путь к индексу по умолчанию.
    """
    path = urlparse(repo_url).path
    if path.rsplit("/", 1)[-1] in INDEX_NAMES:
        return repo_url
    return (f"{repo_url.rstrip('/')}/dists/{DEFAULT_SUITE}/"
            f"{DEFAULT_COMPONENT}/binary-{DEFAULT_ARCH}/Packages.gz")


def _decompress(data, url):
    """Распаковывает индекс в зависимости от расширения файла."""
    path = urlparse(url).path
    try:
        if path.endswith(".gz"):
            data = gzip.decompress(data)
        elif path.endswith(".xz"):
            data = lzma.decompress(data)
    except (OSError, EOFError, lzma.LZMAError) as exc:
        raise RepositoryError(
            f"не удалось распаковать индекс '{url}': {exc}") from exc
    return data.decode("utf-8", errors="replace")


def fetch_index(index_url):
    """Скачивает индекс пакетов и возвращает его текст."""
    request = urllib.request.Request(
        index_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(
                request, timeout=REQUEST_TIMEOUT) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        raise RepositoryError(
            f"сервер вернул ошибку {exc.code} для '{index_url}'") from exc
    except urllib.error.URLError as exc:
        raise RepositoryError(
            f"не удалось подключиться к '{index_url}': {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise RepositoryError(
            f"ошибка загрузки '{index_url}': {exc}") from exc
    return _decompress(data, index_url)


def _parse_stanza(lines):
    """Превращает строки одной записи в словарь полей."""
    stanza = {}
    field = None
    for line in lines:
        if line.startswith(CONTINUATION_CHARS) and field is not None:
            stanza[field] += "\n" + line.strip()
            continue
        name, separator, value = line.partition(":")
        if not separator:
            continue
        field = name.strip()
        stanza[field] = value.strip()
    return stanza


def iter_stanzas(text):
    """Перебирает записи индекса; каждая запись — словарь полей."""
    lines = []
    for line in text.splitlines():
        if line.strip():
            lines.append(line)
        elif lines:
            yield _parse_stanza(lines)
            lines = []
    if lines:
        yield _parse_stanza(lines)


def find_package(text, name, version):
    """Ищет в индексе запись пакета с заданным именем и версией.

    Бросает RepositoryError, если пакета нет или нет нужной версии;
    во втором случае в сообщении перечислены доступные версии.
    """
    versions = []
    for stanza in iter_stanzas(text):
        if stanza.get("Package") != name:
            continue
        if stanza.get("Version") == version:
            return stanza
        versions.append(stanza.get("Version", "?"))
    if not versions:
        raise RepositoryError(f"пакет '{name}' не найден в репозитории")
    raise RepositoryError(
        f"версия '{version}' пакета '{name}' не найдена; "
        f"доступные версии: {', '.join(versions)}")
