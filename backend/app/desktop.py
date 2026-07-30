import logging
import os
import socket
import sys
import threading

import uvicorn

from app.core.logging import configure_logging

logger = logging.getLogger("odin.desktop")


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        try:
            server.bind((host, port))
        except OSError:
            return False
    return True


def main() -> int:
    configure_logging()
    if os.getenv("ODIN_CREDENTIAL_STORE_SELF_TEST") == "1":
        from app.services.credential_store import credential_store

        capability = credential_store.capability(refresh=True)
        return 0 if capability.available else 4
    try:
        from app.core.config import settings
    except Exception:
        logger.error(
            "Odin kunde inte läsa den lokala konfigurationen. "
            "Kontrollera miljövariablerna utan att dela hemliga värden."
        )
        return 2

    if settings.desktop_host not in {"127.0.0.1", "localhost"}:
        logger.error("Desktop-backend måste bindas till localhost.")
        return 2

    if not port_is_available(settings.desktop_host, settings.desktop_port):
        logger.error(
            "Port %s används redan. Stäng den andra processen och försök igen.",
            settings.desktop_port,
        )
        return 3

    logger.info(
        "Startar Project Odin lokalt på http://%s:%s",
        settings.desktop_host,
        settings.desktop_port,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            "app.main:app",
            host=settings.desktop_host,
            port=settings.desktop_port,
            log_level="info",
            access_log=False,
        )
    )

    def monitor_parent() -> None:
        try:
            sys.stdin.readline()
        except OSError:
            return
        server.should_exit = True

    threading.Thread(target=monitor_parent, daemon=True).start()
    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
