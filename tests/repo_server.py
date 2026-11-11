"""Локальный HTTP-сервер с индексами пакетов для тестов без интернета."""

import functools
import gzip
import lzma
import os
import shutil
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

FIXTURE_INDEX = os.path.join(os.path.dirname(__file__), "..", "fixtures",
                             "apt", "Packages")
INDEX_DIR = "dists/jammy/main/binary-amd64"


class _QuietHandler(SimpleHTTPRequestHandler):
    """Обработчик запросов, не печатающий журнал в консоль."""

    def log_message(self, *args):
        """Подавляет вывод журнала запросов."""


class RepoServer:
    """Раздаёт тестовый индекс в виде Packages, .gz, .xz и битого .gz.

    Используется как контекстный менеджер; base_url — корень архива.
    """

    def __enter__(self):
        """Готовит файлы во временном каталоге и запускает сервер."""
        self._root = tempfile.mkdtemp()
        index_dir = os.path.join(self._root, INDEX_DIR)
        os.makedirs(index_dir)
        with open(FIXTURE_INDEX, "rb") as source:
            data = source.read()
        self._write(index_dir, "Packages", data)
        self._write(index_dir, "Packages.gz", gzip.compress(data))
        self._write(index_dir, "Packages.xz", lzma.compress(data))
        self._write(self._root, "broken/Packages.gz", b"not gzip")
        handler = functools.partial(_QuietHandler, directory=self._root)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self._server.serve_forever,
                         daemon=True).start()
        self.base_url = f"http://127.0.0.1:{self._server.server_port}"
        return self

    def __exit__(self, *exc_info):
        """Останавливает сервер и удаляет временные файлы."""
        self._server.shutdown()
        self._server.server_close()
        shutil.rmtree(self._root)

    @staticmethod
    def _write(directory, name, data):
        """Записывает файл, создавая промежуточные каталоги."""
        path = os.path.join(directory, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as target:
            target.write(data)
