"""Persistencia segura en JSON con bloqueo fcntl.flock y auditoria de usuario Linux."""

import fcntl
import json
import os
import pwd
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def obtener_usuario_linux() -> str:
    """Obtiene el nombre del usuario de Linux actual mediante uid y pwd."""
    uid = os.getuid()
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return f"uid-{uid}"


class AlmacenJSON:
    """Gestiona lectura y escritura concurrente segura en disco."""

    def __init__(self, ruta_archivo: str | Path = "data/inventario.json") -> None:
        self.ruta = Path(ruta_archivo)
        self.ruta_lock = Path(f"{self.ruta}.lock")
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        if not self.ruta.exists():
            self._escribir_atomico({"activos": [], "licencias": []})

    @contextmanager
    def _bloqueo_exclusivo(self):
        """Adquiere un bloqueo exclusivo a nivel de sistema operativo."""
        self.ruta_lock.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta_lock, "w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _leer_sin_lock(self) -> dict[str, Any]:
        if not self.ruta.exists():
            return {"activos": [], "licencias": []}
        contenido = self.ruta.read_text(encoding="utf-8").strip()
        if not contenido:
            return {"activos": [], "licencias": []}
        return json.loads(contenido)

    def _escribir_atomico(self, datos: dict[str, Any]) -> None:
        tmp_path = self.ruta.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.ruta)

    def leer_datos(self) -> dict[str, Any]:
        """Lee los datos bajo bloqueo para evitar lecturas parciales."""
        with self._bloqueo_exclusivo():
            return self._leer_sin_lock()

    def actualizar_datos(
        self, mutador: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> dict[str, Any]:
        """Ejecuta una transaccion atomica: bloquea -> lee -> modifica -> guarda."""
        with self._bloqueo_exclusivo():
            datos = self._leer_sin_lock()
            nuevos_datos = mutador(datos)
            self._escribir_atomico(nuevos_datos)
            return nuevos_datos
