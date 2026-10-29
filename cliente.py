"""Cliente de consola: envía tareas por socket y muestra el resultado."""

from __future__ import annotations

import json
import socket
import sys
import uuid

from config import ENCODING, HOST, PORT
from protocolo import ProtocoloError, enviar, recibir


TIPOS = ("echo", "reverse", "sum", "sleep")


def conectar(host: str = HOST, port: int = PORT) -> socket.socket:
    sock = socket.create_connection((host, port))
    return sock


def enviar_tarea(sock: socket.socket, tipo: str, payload, buffer: bytearray) -> dict:
    mensaje = {"id": str(uuid.uuid4())[:8], "tipo": tipo, "payload": payload}
    enviar(sock, mensaje)
    return recibir(sock, buffer)


def _payload_desde_texto(tipo: str, texto: str):
    if tipo == "sum":
        return [float(p.strip()) for p in texto.split(",") if p.strip()]
    if tipo == "sleep":
        return float(texto)
    if tipo == "echo":
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            return texto
    return texto


def menu() -> None:
    host = HOST
    port = PORT
    if len(sys.argv) >= 3:
        host, port = sys.argv[1], int(sys.argv[2])

    print(f"Conectando a {host}:{port} ...")
    sock = conectar(host, port)
    buffer = bytearray()
    print("Tipos: echo | reverse | sum | sleep | salir")
    print("Ejemplos de payload: hola  |  1,2,3  |  2")
    try:
        while True:
            tipo = input("tipo> ").strip().lower()
            if tipo in {"salir", "exit", "quit", ""}:
                break
            if tipo not in TIPOS:
                print(f"Tipo desconocido. Usá: {', '.join(TIPOS)}")
                continue
            texto = input("payload> ")
            try:
                payload = _payload_desde_texto(tipo, texto)
            except ValueError as exc:
                print(f"Payload inválido: {exc}")
                continue
            try:
                respuesta = enviar_tarea(sock, tipo, payload, buffer)
            except ProtocoloError as exc:
                print(f"Conexión perdida: {exc}")
                break
            print(json.dumps(respuesta, ensure_ascii=False, indent=2))
    finally:
        sock.close()
        print("Desconectado.")


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\nCliente interrumpido.")
    except ConnectionRefusedError:
        print("No hay servidor escuchando. Ejecutá primero: python servidor.py")
        sys.exit(1)
