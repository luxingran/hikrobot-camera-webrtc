from __future__ import annotations

from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)

from pathlib import Path
import functools


STATIC_DIR = (
    Path(__file__)
    .resolve()
    .parent
    / "static"
)


def create_web_server(
    host: str = "0.0.0.0",
    port: int = 8080,
):

    handler = functools.partial(
        SimpleHTTPRequestHandler,
        directory=str(STATIC_DIR),
    )

    return ThreadingHTTPServer(
        (host, port),
        handler,
    )


def run_web_server(
    host: str = "0.0.0.0",
    port: int = 8080,
):

    server = create_web_server(
        host,
        port,
    )

    print(
        f"Web server listening "
        f"on {host}:{port}"
    )

    try:
        server.serve_forever()

    finally:
        server.server_close()


if __name__ == "__main__":

    run_web_server()