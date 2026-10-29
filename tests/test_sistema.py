"""Pruebas unitarias del pool de tareas e integración por socket."""

from __future__ import annotations

import socket
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from protocolo import enviar, recibir
from servidor import ServidorTareas
from tareas import TareaError, ejecutar


class TestTareas(unittest.TestCase):
    def test_echo(self):
        self.assertEqual(ejecutar("echo", {"a": 1}), {"a": 1})

    def test_reverse(self):
        self.assertEqual(ejecutar("reverse", "redes"), "seder")

    def test_sum(self):
        self.assertEqual(ejecutar("sum", [1, 2, 3.5]), 6.5)

    def test_sum_invalido(self):
        with self.assertRaises(TareaError):
            ejecutar("sum", "no-lista")

    def test_tipo_desconocido(self):
        with self.assertRaises(TareaError):
            ejecutar("borrar_disco", None)


class TestIntegracionSocket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = ServidorTareas(host="127.0.0.1", port=0, workers=2)
        cls.servidor.iniciar(en_hilo=True)
        for _ in range(50):
            if cls.servidor.puerto_real:
                break
            time.sleep(0.02)
        cls.port = cls.servidor.puerto_real

    @classmethod
    def tearDownClass(cls):
        cls.servidor.detener()

    def _pedir(self, tipo, payload):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        buffer = bytearray()
        try:
            enviar(sock, {"id": "t1", "tipo": tipo, "payload": payload})
            return recibir(sock, buffer)
        finally:
            sock.close()

    def test_sum_por_socket(self):
        respuesta = self._pedir("sum", [10, 20, 12])
        self.assertTrue(respuesta["ok"])
        self.assertEqual(respuesta["resultado"], 42)

    def test_error_por_socket(self):
        respuesta = self._pedir("reverse", 123)
        self.assertFalse(respuesta["ok"])
        self.assertIn("texto", respuesta["error"])

    def test_dos_clientes_concurrentes(self):
        resultados = []

        def worker():
            resultados.append(self._pedir("echo", "ok"))

        hilos = [threading.Thread(target=worker) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=5)
        self.assertEqual(len(resultados), 2)
        self.assertTrue(all(r["ok"] and r["resultado"] == "ok" for r in resultados))


if __name__ == "__main__":
    unittest.main()
