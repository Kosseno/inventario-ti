"""Punto de entrada principal del inventario de activos de TI."""

import argparse
import curses
from pathlib import Path

from services import InventarioService
from storage import AlmacenJSON
from tui import ejecutar_tui


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sistema de Inventario de Activos de TI (Terminal / Cron)"
    )
    parser.add_argument(
        "--alertas",
        action="store_true",
        help="Genera reporte de garantias por vencer y licencias excedidas sin UI.",
    )
    parser.add_argument(
        "--db",
        default="data/inventario.json",
        help="Ruta del archivo JSON de datos (por defecto: data/inventario.json).",
    )
    parser.add_argument(
        "--salida-alertas",
        default="data/alertas_cron.txt",
        help="Archivo de salida cuando se usa --alertas.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    servicio = InventarioService(AlmacenJSON(Path(args.db)))

    if args.alertas:
        archivo = servicio.generar_archivo_alertas(args.salida_alertas)
        print(f"Reporte de alertas generado en: {archivo}")
        return

    curses.wrapper(ejecutar_tui, servicio)


if __name__ == "__main__":
    main()
