"""Servidor TCP que recibe tareas y las reparte a un pool de hilos."""

from __future__ import annotations

import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from config import BACKLOG, HOST, PORT, TAMANIO_POOL
from protocolo import ProtocoloError, enviar, recibir
from tareas import TareaError, ejecutar


class ServidorTareas:
    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        workers: int = TAMANIO_POOL,
    ) -> None:
        self.host = host
        self.port = port
        self.workers = workers
        self._sock: Optional[socket.socket] = None
        self._pool: Optional[ThreadPoolExecutor] = None
        self._vivo = threading.Event()
        self._hilo_aceptar: Optional[threading.Thread] = None
        self.puerto_real: Optional[int] = None

    def iniciar(self, en_hilo: bool = False) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(BACKLOG)
        self._sock.settimeout(1.0)
        self.puerto_real = self._sock.getsockname()[1]
        self._pool = ThreadPoolExecutor(max_workers=self.workers)
        self._vivo.set()
        print(
            f"Servidor en {self.host}:{self.puerto_real} "
            f"(pool de {self.workers} workers)"
        )
        if en_hilo:
            self._hilo_aceptar = threading.Thread(
                target=self._bucle_aceptar, name="aceptar", daemon=True
            )
            self._hilo_aceptar.start()
        else:
            self._bucle_aceptar()

    def detener(self) -> None:
        self._vivo.clear()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._hilo_aceptar is not None:
            self._hilo_aceptar.join(timeout=3)
            self._hilo_aceptar = None
        if self._pool is not None:
            self._pool.shutdown(wait=True)
            self._pool = None

    def _bucle_aceptar(self) -> None:
        assert self._sock is not None
        while self._vivo.is_set():
            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            hilo = threading.Thread(
                target=self._atender_cliente,
                args=(conn, addr),
                daemon=True,
            )
            hilo.start()

    def _atender_cliente(self, conn: socket.socket, addr) -> None:
        buffer = bytearray()
        print(f"Cliente conectado: {addr}")
        try:
            with conn:
                while self._vivo.is_set():
                    try:
                        mensaje = recibir(conn, buffer)
                    except ProtocoloError:
                        break
                    respuesta = self._procesar(mensaje)
                    enviar(conn, respuesta)
        finally:
            print(f"Cliente desconectado: {addr}")

    def _procesar(self, mensaje: dict) -> dict:
        tarea_id = mensaje.get("id", "")
        tipo = mensaje.get("tipo", "")
        payload = mensaje.get("payload")
        if self._pool is None:
            return {"id": tarea_id, "ok": False, "error": "servidor detenido"}
        futuro = self._pool.submit(ejecutar, tipo, payload)
        try:
            resultado = futuro.result()
            return {"id": tarea_id, "ok": True, "resultado": resultado}
        except TareaError as exc:
            return {"id": tarea_id, "ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 — se informa al cliente
            return {"id": tarea_id, "ok": False, "error": f"error interno: {exc}"}


def main() -> None:
    servidor = ServidorTareas()
    try:
        servidor.iniciar()
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
    finally:
        servidor.detener()


if __name__ == "__main__":
    main()
