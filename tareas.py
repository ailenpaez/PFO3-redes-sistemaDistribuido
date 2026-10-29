"""Tipos de tarea que ejecutan los workers del pool."""

from __future__ import annotations

import time
from typing import Any


class TareaError(ValueError):
    """Payload o tipo de tarea inválido."""


def ejecutar(tipo: str, payload: Any) -> Any:
    tipo = (tipo or "").strip().lower()
    if tipo == "echo":
        return payload
    if tipo == "reverse":
        if not isinstance(payload, str):
            raise TareaError("reverse espera un texto")
        return payload[::-1]
    if tipo == "sum":
        if not isinstance(payload, list) or not payload:
            raise TareaError("sum espera una lista de números no vacía")
        try:
            return sum(float(n) for n in payload)
        except (TypeError, ValueError) as exc:
            raise TareaError("sum espera solo números") from exc
    if tipo == "sleep":
        segundos = float(payload) if not isinstance(payload, dict) else float(
            payload.get("segundos", 0)
        )
        if segundos < 0 or segundos > 30:
            raise TareaError("sleep espera segundos entre 0 y 30")
        time.sleep(segundos)
        return {"dormido": segundos}
    raise TareaError(f"tipo de tarea desconocido: {tipo!r}")
