"""Mensajes JSON delimitados por salto de línea."""

from __future__ import annotations

import json
from typing import Any

from config import ENCODING


class ProtocoloError(Exception):
    """El socket se cerró o el mensaje no es JSON válido."""


def enviar(sock, mensaje: dict[str, Any]) -> None:
    linea = json.dumps(mensaje, ensure_ascii=False) + "\n"
    sock.sendall(linea.encode(ENCODING))


def recibir(sock, buffer: bytearray) -> dict[str, Any]:
    """Lee hasta un \\n, reutilizando *buffer* para fragmentos parciales."""
    while True:
        salto = buffer.find(b"\n")
        if salto != -1:
            linea = bytes(buffer[:salto])
            del buffer[: salto + 1]
            texto = linea.decode(ENCODING).strip()
            if not texto:
                continue
            try:
                datos = json.loads(texto)
            except json.JSONDecodeError as exc:
                raise ProtocoloError(f"JSON inválido: {exc}") from exc
            if not isinstance(datos, dict):
                raise ProtocoloError("el mensaje debe ser un objeto JSON")
            return datos

        fragmento = sock.recv(4096)
        if not fragmento:
            raise ProtocoloError("conexión cerrada")
        buffer.extend(fragmento)
