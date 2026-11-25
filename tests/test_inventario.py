"""Pruebas unitarias para la logica de negocio del inventario de TI."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from services import InventarioService
from storage import AlmacenJSON


@pytest.fixture
def servicio(tmp_path: Path) -> InventarioService:
    almacen = AlmacenJSON(tmp_path / "test_inventario.json")
    return InventarioService(almacen)


def test_registrar_y_listar_activo(servicio: InventarioService) -> None:
    activo = servicio.registrar_activo(
        codigo="ACT-001",
        tipo="Laptop",
        marca="Dell",
        modelo="Latitude 5440",
        numero_serie="SN-DELL-01",
        fecha_compra="2025-01-15",
        costo=1200.0,
    )
    assert activo.codigo == "ACT-001"
    assert activo.estado == "bodega"
    assert len(servicio.listar_activos()) == 1


def test_editar_y_dar_de_baja_activo(servicio: InventarioService) -> None:
    servicio.registrar_activo(
        "ACT-002", "Monitor", "LG", "27UL500", "SN-LG-02", "2024-05-01", 350.0
    )
    editado = servicio.editar_activo("ACT-002", estado="reparacion")
    assert editado.estado == "reparacion"

    baja = servicio.dar_de_baja_activo("ACT-002", "Pantalla rota")
    assert baja.estado == "baja"
    assert baja.historial[-1].accion == "BAJA"
    assert baja.historial[-1].usuario_sistema != ""


def test_asignar_y_devolver_con_auditoria_linux(servicio: InventarioService) -> None:
    servicio.registrar_activo(
        "ACT-003",
        "Laptop",
        "Lenovo",
        "ThinkPad T14",
        "SN-LEN-03",
        "2025-03-01",
        1100.0,
    )
    asignado = servicio.asignar_activo("ACT-003", "Maria Lopez")
    assert asignado.estado == "en uso"
    assert asignado.empleado_asignado == "Maria Lopez"
    assert asignado.historial[-1].usuario_sistema != ""

    devuelto = servicio.devolver_activo("ACT-003", "bodega")
    assert devuelto.estado == "bodega"
    assert devuelto.empleado_asignado is None
    assert len(devuelto.historial) == 3


def test_no_permite_asignar_equipo_ya_asignado(servicio: InventarioService) -> None:
    servicio.registrar_activo(
        "ACT-004", "Laptop", "HP", "ProBook", "SN-HP-04", "2025-02-01", 950.0
    )
    servicio.asignar_activo("ACT-004", "Carlos Ruiz")
    with pytest.raises(ValueError, match="ya esta asignado"):
        servicio.asignar_activo("ACT-004", "Ana Gomez")


def test_alertas_garantias_30_dias(servicio: InventarioService) -> None:
    hoy = date(2026, 11, 19)
    en_15_dias = (hoy + timedelta(days=15)).strftime("%Y-%m-%d")
    en_90_dias = (hoy + timedelta(days=90)).strftime("%Y-%m-%d")

    servicio.registrar_activo(
        "ACT-005",
        "Servidor",
        "Dell",
        "PowerEdge",
        "SN-SRV-05",
        "2024-01-01",
        3000.0,
        fecha_garantia=en_15_dias,
    )
    servicio.registrar_activo(
        "ACT-006",
        "Laptop",
        "Apple",
        "MacBook Pro",
        "SN-MAC-06",
        "2025-01-01",
        2200.0,
        fecha_garantia=en_90_dias,
    )

    alertas = servicio.alertas_garantias(dias_limite=30, fecha_referencia=hoy)
    assert len(alertas) == 1
    assert alertas[0]["codigo"] == "ACT-005"


def test_control_licencias_y_aviso_exceso(servicio: InventarioService) -> None:
    servicio.registrar_licencia("LIC-01", "JetBrains All Products", 2, "2027-01-01")
    servicio.asignar_licencia("LIC-01", "Dev 1")
    servicio.asignar_licencia("LIC-01", "Dev 2")
    assert len(servicio.licencias_excedidas()) == 0

    lic = servicio.asignar_licencia("LIC-01", "Dev 3")
    assert lic.excedida is True
    assert len(servicio.licencias_excedidas()) == 1


def test_busqueda_y_vista_por_empleado(servicio: InventarioService) -> None:
    servicio.registrar_activo(
        "ACT-007", "Laptop", "Dell", "XPS 13", "SN-XPS-07", "2025-06-01", 1400.0
    )
    servicio.asignar_activo("ACT-007", "Sofia Mendez")
    servicio.registrar_licencia("LIC-02", "Docker Business", 5, "2027-06-01")
    servicio.asignar_licencia("LIC-02", "Sofia Mendez")

    por_serie = servicio.buscar_activos("serie", "XPS-07")
    assert len(por_serie) == 1

    ficha = servicio.consultar_empleado("Sofia Mendez")
    assert len(ficha["activos"]) == 1
    assert len(ficha["licencias"]) == 1


def test_depreciacion_lineal_y_exportacion_csv(
    servicio: InventarioService, tmp_path: Path
) -> None:
    servicio.registrar_activo(
        "ACT-008", "Laptop", "Dell", "Latitude", "SN-DEP-08", "2024-11-19", 1000.0
    )
    reporte = servicio.calcular_depreciacion_lineal(
        vida_util_anios=4, fecha_corte=date(2026, 11, 19)
    )
    assert reporte[0]["valor_actual"] == pytest.approx(500.0, abs=2.0)

    csv_out = servicio.exportar_reporte_depreciacion(tmp_path / "dep.csv")
    assert csv_out.exists()
    assert "ACT-008" in csv_out.read_text(encoding="utf-8")


def test_modo_headless_cron_alertas(
    servicio: InventarioService, tmp_path: Path
) -> None:
    ayer = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    servicio.registrar_activo(
        "ACT-009",
        "Router",
        "Cisco",
        "ISR",
        "SN-CSC-09",
        "2023-01-01",
        800.0,
        fecha_garantia=ayer,
    )
    servicio.registrar_licencia("LIC-03", "Figma", 1, "2027-01-01")
    servicio.asignar_licencia("LIC-03", "Disenador 1")
    servicio.asignar_licencia("LIC-03", "Disenador 2")

    salida = servicio.generar_archivo_alertas(tmp_path / "cron_alertas.txt")
    contenido = salida.read_text(encoding="utf-8")
    assert "ACT-009" in contenido
    assert "Figma" in contenido
    assert "EXCESO DE 1" in contenido


def test_importar_csv_masivo(servicio: InventarioService, tmp_path: Path) -> None:
    archivo_csv = tmp_path / "lote.csv"
    archivo_csv.write_text(
        "codigo,tipo,marca,modelo,numero_serie,fecha_compra,fecha_garantia,costo,estado\n"
        "ACT-100,Laptop,HP,EliteBook,SN-100,2025-01-01,2027-01-01,1100,bodega\n"
        "ACT-101,Monitor,Samsung,Odyssey,SN-101,2025-02-01,2027-02-01,400,bodega\n",
        encoding="utf-8",
    )
    res = servicio.importar_csv(archivo_csv)
    assert res == {"importados": 2, "omitidos": 0}
    assert len(servicio.listar_activos()) == 2


def test_auditoria_fisica_faltantes(servicio: InventarioService) -> None:
    servicio.registrar_activo(
        "ACT-200", "Laptop", "Dell", "Vostro", "SN-200", "2025-01-01", 900.0
    )
    servicio.registrar_activo(
        "ACT-201", "Monitor", "Asus", "ProArt", "SN-201", "2025-01-01", 500.0
    )
    servicio.marcar_verificado_auditoria("ACT-200", True)
    faltantes = servicio.listar_faltantes_auditoria()
    assert [a.codigo for a in faltantes] == ["ACT-201"]


def test_detectar_series_duplicadas(servicio: InventarioService) -> None:
    servicio.registrar_activo(
        "ACT-300", "Laptop", "Dell", "XPS", "SN-DUP-99", "2025-01-01", 1000.0
    )
    servicio.registrar_activo(
        "ACT-301",
        "Laptop",
        "Dell",
        "XPS",
        "SN-DUP-99",
        "2025-01-02",
        1000.0,
        permitir_serie_duplicada=True,
    )
    duplicados = servicio.detectar_series_duplicadas()
    assert "SN-DUP-99" in duplicados
    assert len(duplicados["SN-DUP-99"]) == 2
