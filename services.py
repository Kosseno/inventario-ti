"""Logica de negocio del sistema de inventario de activos de TI."""

import csv
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from models import ESTADOS_VALIDOS, Activo, Licencia, MovimientoHistorial
from storage import AlmacenJSON, obtener_usuario_linux


def _ahora_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class InventarioService:
    """Servicio principal con todas las operaciones del inventario."""

    def __init__(self, almacen: AlmacenJSON | None = None) -> None:
        self.almacen = almacen or AlmacenJSON()

    # --- LECTURA DE COLECCIONES ---

    def listar_activos(self) -> list[Activo]:
        datos = self.almacen.leer_datos()
        return [Activo.from_dict(item) for item in datos.get("activos", [])]

    def listar_licencias(self) -> list[Licencia]:
        datos = self.almacen.leer_datos()
        return [Licencia.from_dict(item) for item in datos.get("licencias", [])]

    def obtener_activo(self, codigo: str) -> Activo | None:
        for activo in self.listar_activos():
            if activo.codigo.lower() == codigo.strip().lower():
                return activo
        return None

    # --- CRUD DE ACTIVOS ---

    def registrar_activo(
        self,
        codigo: str,
        tipo: str,
        marca: str,
        modelo: str,
        numero_serie: str,
        fecha_compra: str,
        costo: float,
        estado: str = "bodega",
        fecha_garantia: str | None = None,
        permitir_serie_duplicada: bool = False,
    ) -> Activo:
        codigo = codigo.strip().upper()
        numero_serie = numero_serie.strip()
        estado = estado.strip().lower()

        if estado not in ESTADOS_VALIDOS:
            raise ValueError(f"Estado invalido: {estado}. Validos: {ESTADOS_VALIDOS}")
        if costo < 0:
            raise ValueError("El costo no puede ser negativo.")

        # Validar fechas YYYY-MM-DD
        datetime.strptime(fecha_compra, "%Y-%m-%d")
        garantia_final = fecha_garantia.strip() if fecha_garantia else fecha_compra
        datetime.strptime(garantia_final, "%Y-%m-%d")

        usuario = obtener_usuario_linux()
        nuevo = Activo(
            codigo=codigo,
            tipo=tipo.strip(),
            marca=marca.strip(),
            modelo=modelo.strip(),
            numero_serie=numero_serie,
            fecha_compra=fecha_compra,
            fecha_garantia=garantia_final,
            costo=float(costo),
            estado=estado,
            historial=[
                MovimientoHistorial(
                    fecha=_ahora_iso(),
                    accion="ALTA",
                    empleado="N/A",
                    usuario_sistema=usuario,
                    detalle=f"Registro inicial ({estado})",
                )
            ],
        )

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            activos = [Activo.from_dict(a) for a in datos.get("activos", [])]
            if any(a.codigo == codigo for a in activos):
                raise ValueError(f"Ya existe un activo con el codigo {codigo}.")
            if not permitir_serie_duplicada and any(
                a.numero_serie.lower() == numero_serie.lower() for a in activos
            ):
                raise ValueError(
                    f"El numero de serie '{numero_serie}' ya esta registrado."
                )
            activos.append(nuevo)
            datos["activos"] = [a.to_dict() for a in activos]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return nuevo

    def editar_activo(
        self,
        codigo: str,
        tipo: str | None = None,
        marca: str | None = None,
        modelo: str | None = None,
        numero_serie: str | None = None,
        fecha_compra: str | None = None,
        fecha_garantia: str | None = None,
        costo: float | None = None,
        estado: str | None = None,
    ) -> Activo:
        usuario = obtener_usuario_linux()
        resultado: dict[str, Activo] = {}

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            activos = [Activo.from_dict(a) for a in datos.get("activos", [])]
            encontrado = next(
                (a for a in activos if a.codigo == codigo.strip().upper()), None
            )
            if not encontrado:
                raise ValueError(f"Activo {codigo} no encontrado.")

            if tipo:
                encontrado.tipo = tipo.strip()
            if marca:
                encontrado.marca = marca.strip()
            if modelo:
                encontrado.modelo = modelo.strip()
            if numero_serie:
                encontrado.numero_serie = numero_serie.strip()
            if fecha_compra:
                datetime.strptime(fecha_compra, "%Y-%m-%d")
                encontrado.fecha_compra = fecha_compra
            if fecha_garantia:
                datetime.strptime(fecha_garantia, "%Y-%m-%d")
                encontrado.fecha_garantia = fecha_garantia
            if costo is not None:
                if costo < 0:
                    raise ValueError("El costo no puede ser negativo.")
                encontrado.costo = float(costo)
            if estado:
                est = estado.strip().lower()
                if est not in ESTADOS_VALIDOS:
                    raise ValueError(f"Estado invalido: {est}")
                encontrado.estado = est

            encontrado.historial.append(
                MovimientoHistorial(
                    fecha=_ahora_iso(),
                    accion="EDICION",
                    empleado=encontrado.empleado_asignado or "N/A",
                    usuario_sistema=usuario,
                    detalle="Actualizacion de ficha del activo",
                )
            )
            resultado["activo"] = encontrado
            datos["activos"] = [a.to_dict() for a in activos]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return resultado["activo"]

    def dar_de_baja_activo(
        self, codigo: str, motivo: str = "Baja definitiva"
    ) -> Activo:
        usuario = obtener_usuario_linux()
        resultado: dict[str, Activo] = {}

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            activos = [Activo.from_dict(a) for a in datos.get("activos", [])]
            encontrado = next(
                (a for a in activos if a.codigo == codigo.strip().upper()), None
            )
            if not encontrado:
                raise ValueError(f"Activo {codigo} no encontrado.")

            empleado_previo = encontrado.empleado_asignado or "N/A"
            encontrado.estado = "baja"
            encontrado.empleado_asignado = None
            encontrado.historial.append(
                MovimientoHistorial(
                    fecha=_ahora_iso(),
                    accion="BAJA",
                    empleado=empleado_previo,
                    usuario_sistema=usuario,
                    detalle=motivo,
                )
            )
            resultado["activo"] = encontrado
            datos["activos"] = [a.to_dict() for a in activos]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return resultado["activo"]

    # --- ASIGNACIONES Y DEVOLUCIONES ---

    def asignar_activo(self, codigo: str, empleado: str) -> Activo:
        empleado = empleado.strip()
        if not empleado:
            raise ValueError("Debe especificar el nombre del empleado.")
        usuario = obtener_usuario_linux()
        resultado: dict[str, Activo] = {}

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            activos = [Activo.from_dict(a) for a in datos.get("activos", [])]
            encontrado = next(
                (a for a in activos if a.codigo == codigo.strip().upper()), None
            )
            if not encontrado:
                raise ValueError(f"Activo {codigo} no encontrado.")
            if encontrado.estado == "baja":
                raise ValueError("No se puede asignar un activo dado de baja.")
            if encontrado.estado == "reparacion":
                raise ValueError("El activo esta en reparacion.")
            if encontrado.empleado_asignado:
                raise ValueError(
                    f"El activo ya esta asignado a {encontrado.empleado_asignado}."
                )

            encontrado.empleado_asignado = empleado
            encontrado.estado = "en uso"
            encontrado.historial.append(
                MovimientoHistorial(
                    fecha=_ahora_iso(),
                    accion="ASIGNACION",
                    empleado=empleado,
                    usuario_sistema=usuario,
                    detalle="Entrega de equipo",
                )
            )
            resultado["activo"] = encontrado
            datos["activos"] = [a.to_dict() for a in activos]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return resultado["activo"]

    def devolver_activo(
        self, codigo: str, estado_destino: str = "bodega", nota: str = "Devolucion"
    ) -> Activo:
        estado_destino = estado_destino.strip().lower()
        if estado_destino not in ("bodega", "reparacion"):
            raise ValueError("Al devolver, el estado debe ser 'bodega' o 'reparacion'.")
        usuario = obtener_usuario_linux()
        resultado: dict[str, Activo] = {}

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            activos = [Activo.from_dict(a) for a in datos.get("activos", [])]
            encontrado = next(
                (a for a in activos if a.codigo == codigo.strip().upper()), None
            )
            if not encontrado:
                raise ValueError(f"Activo {codigo} no encontrado.")
            if not encontrado.empleado_asignado:
                raise ValueError("El activo no esta asignado a ningun empleado.")

            empleado_anterior = encontrado.empleado_asignado
            encontrado.empleado_asignado = None
            encontrado.estado = estado_destino
            encontrado.historial.append(
                MovimientoHistorial(
                    fecha=_ahora_iso(),
                    accion="DEVOLUCION",
                    empleado=empleado_anterior,
                    usuario_sistema=usuario,
                    detalle=f"{nota} -> {estado_destino}",
                )
            )
            resultado["activo"] = encontrado
            datos["activos"] = [a.to_dict() for a in activos]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return resultado["activo"]

    # --- GARANTIAS Y LICENCIAS ---

    def alertas_garantias(
        self, dias_limite: int = 30, fecha_referencia: date | None = None
    ) -> list[dict[str, Any]]:
        """Devuelve activos activos cuya garantia vence en <= dias_limite dias."""
        hoy = fecha_referencia or date.today()
        alertas: list[dict[str, Any]] = []

        for activo in self.listar_activos():
            if activo.estado == "baja":
                continue
            vencimiento = datetime.strptime(activo.fecha_garantia, "%Y-%m-%d").date()
            dias_restantes = (vencimiento - hoy).days
            if dias_restantes <= dias_limite:
                alertas.append(
                    {
                        "codigo": activo.codigo,
                        "equipo": f"{activo.tipo} {activo.marca} {activo.modelo}",
                        "numero_serie": activo.numero_serie,
                        "fecha_garantia": activo.fecha_garantia,
                        "dias_restantes": dias_restantes,
                        "empleado": activo.empleado_asignado or "En bodega/taller",
                    }
                )
        return sorted(alertas, key=lambda x: x["dias_restantes"])

    def registrar_licencia(
        self,
        codigo: str,
        software: str,
        puestos_comprados: int,
        fecha_vencimiento: str,
        costo_unitario: float = 0.0,
    ) -> Licencia:
        codigo = codigo.strip().upper()
        if puestos_comprados <= 0:
            raise ValueError("Los puestos comprados deben ser mayores a 0.")
        datetime.strptime(fecha_vencimiento, "%Y-%m-%d")

        nueva = Licencia(
            codigo=codigo,
            software=software.strip(),
            puestos_comprados=puestos_comprados,
            fecha_vencimiento=fecha_vencimiento,
            costo_unitario=float(costo_unitario),
        )

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            licencias = [Licencia.from_dict(lic) for lic in datos.get("licencias", [])]
            if any(lic.codigo == codigo for lic in licencias):
                raise ValueError(f"Ya existe la licencia {codigo}.")
            licencias.append(nueva)
            datos["licencias"] = [lic.to_dict() for lic in licencias]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return nueva

    def asignar_licencia(self, codigo: str, empleado: str) -> Licencia:
        empleado = empleado.strip()
        if not empleado:
            raise ValueError("Debe indicar el nombre del empleado.")
        resultado: dict[str, Licencia] = {}

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            licencias = [Licencia.from_dict(lic) for lic in datos.get("licencias", [])]
            licencia = next(
                (lic for lic in licencias if lic.codigo == codigo.strip().upper()), None
            )
            if not licencia:
                raise ValueError(f"Licencia {codigo} no encontrada.")
            if empleado in licencia.empleados_asignados:
                raise ValueError(f"{empleado} ya tiene asignada esta licencia.")
            licencia.empleados_asignados.append(empleado)
            resultado["licencia"] = licencia
            datos["licencias"] = [lic.to_dict() for lic in licencias]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return resultado["licencia"]

    def revocar_licencia(self, codigo: str, empleado: str) -> Licencia:
        resultado: dict[str, Licencia] = {}

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            licencias = [Licencia.from_dict(lic) for lic in datos.get("licencias", [])]
            licencia = next(
                (lic for lic in licencias if lic.codigo == codigo.strip().upper()), None
            )
            if not licencia:
                raise ValueError(f"Licencia {codigo} no encontrada.")
            if empleado not in licencia.empleados_asignados:
                raise ValueError(f"{empleado} no tiene asignada esta licencia.")
            licencia.empleados_asignados.remove(empleado)
            resultado["licencia"] = licencia
            datos["licencias"] = [lic.to_dict() for lic in licencias]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return resultado["licencia"]

    def licencias_excedidas(self) -> list[Licencia]:
        """Retorna las licencias donde puestos asignados > puestos comprados."""
        return [lic for lic in self.listar_licencias() if lic.excedida]

    # --- BUSQUEDAS Y VISTA POR EMPLEADO ---

    def buscar_activos(self, criterio: str, valor: str) -> list[Activo]:
        """Busca activos por 'serie', 'empleado' o 'tipo'."""
        termino = valor.strip().lower()
        criterio = criterio.strip().lower()
        activos = self.listar_activos()

        if criterio == "serie":
            return [a for a in activos if termino in a.numero_serie.lower()]
        if criterio == "empleado":
            return [
                a
                for a in activos
                if a.empleado_asignado and termino in a.empleado_asignado.lower()
            ]
        if criterio == "tipo":
            return [a for a in activos if termino in a.tipo.lower()]
        raise ValueError("Criterio invalido. Use 'serie', 'empleado' o 'tipo'.")

    def consultar_empleado(self, nombre_empleado: str) -> dict[str, Any]:
        """Vista: Que tiene asignado este empleado? (hardware + licencias)."""
        objetivo = nombre_empleado.strip().lower()
        equipos = [
            a
            for a in self.listar_activos()
            if a.empleado_asignado and objetivo in a.empleado_asignado.lower()
        ]
        licencias = [
            lic
            for lic in self.listar_licencias()
            if any(objetivo in emp.lower() for emp in lic.empleados_asignados)
        ]
        return {
            "empleado": nombre_empleado.strip(),
            "activos": equipos,
            "licencias": licencias,
        }

    # --- DEPRECIACION LINEAL Y EXPORTACION ---

    def calcular_depreciacion_lineal(
        self,
        vida_util_anios: int = 4,
        valor_residual_pct: float = 0.0,
        fecha_corte: date | None = None,
    ) -> list[dict[str, Any]]:
        """Calcula el valor actual en libros usando depreciacion lineal."""
        if vida_util_anios <= 0:
            raise ValueError("La vida util debe ser mayor a 0 anos.")

        corte = fecha_corte or date.today()
        reporte: list[dict[str, Any]] = []

        for activo in self.listar_activos():
            compra = datetime.strptime(activo.fecha_compra, "%Y-%m-%d").date()
            anios_uso = max(0.0, (corte - compra).days / 365.25)
            valor_residual = round(activo.costo * valor_residual_pct, 2)
            depreciacion_anual = (activo.costo - valor_residual) / vida_util_anios
            depreciacion_acumulada = min(
                activo.costo - valor_residual, depreciacion_anual * anios_uso
            )
            valor_actual = (
                0.0
                if activo.estado == "baja"
                else round(
                    max(valor_residual, activo.costo - depreciacion_acumulada), 2
                )
            )

            reporte.append(
                {
                    "codigo": activo.codigo,
                    "tipo": activo.tipo,
                    "marca_modelo": f"{activo.marca} {activo.modelo}",
                    "estado": activo.estado,
                    "fecha_compra": activo.fecha_compra,
                    "costo_original": round(activo.costo, 2),
                    "depreciacion_acumulada": round(depreciacion_acumulada, 2),
                    "valor_actual": valor_actual,
                }
            )
        return reporte

    def exportar_reporte_depreciacion(
        self,
        ruta_salida: str | Path = "data/reporte_depreciacion.csv",
        vida_util_anios: int = 4,
    ) -> Path:
        filas = self.calcular_depreciacion_lineal(vida_util_anios=vida_util_anios)
        destino = Path(ruta_salida)
        destino.parent.mkdir(parents=True, exist_ok=True)

        with open(destino, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "codigo",
                    "tipo",
                    "marca_modelo",
                    "estado",
                    "fecha_compra",
                    "costo_original",
                    "depreciacion_acumulada",
                    "valor_actual",
                ],
            )
            writer.writeheader()
            writer.writerows(filas)
        return destino

    # --- MODO HEADLESS PARA CRON (--alertas) ---

    def generar_archivo_alertas(
        self, ruta_salida: str | Path = "data/alertas_cron.txt"
    ) -> Path:
        """Escribe garantias por vencer (30 dias) y licencias excedidas sin curses."""
        garantias = self.alertas_garantias(dias_limite=30)
        excedidas = self.licencias_excedidas()
        destino = Path(ruta_salida)
        destino.parent.mkdir(parents=True, exist_ok=True)

        lineas = [
            f"=== REPORTE AUTOMATICO DE ALERTAS TI ({_ahora_iso()}) ===",
            "",
            f"[1] GARANTIAS POR VENCER EN <= 30 DIAS ({len(garantias)}):",
        ]
        if not garantias:
            lineas.append("  - Sin garantias proximas a vencer.")
        else:
            for g in garantias:
                estado_g = (
                    f"VENCIDA hace {abs(g['dias_restantes'])} dias"
                    if g["dias_restantes"] < 0
                    else f"Vence en {g['dias_restantes']} dias"
                )
                lineas.append(
                    f"  - {g['codigo']} | {g['equipo']} (S/N: {g['numero_serie']}) | "
                    f"{g['fecha_garantia']} ({estado_g}) | Resp: {g['empleado']}"
                )

        lineas.extend(["", f"[2] LICENCIAS DE SOFTWARE EXCEDIDAS ({len(excedidas)}):"])
        if not excedidas:
            lineas.append("  - Todas las licencias estan dentro del limite comprado.")
        else:
            for lic in excedidas:
                exceso = lic.puestos_asignados - lic.puestos_comprados
                lineas.append(
                    f"  - {lic.codigo} | {lic.software}: "
                    f"{lic.puestos_asignados}/{lic.puestos_comprados} puestos "
                    f"(EXCESO DE {exceso})"
                )

        destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return destino

    # --- REQUERIMIENTOS OPCIONALES ---

    def importar_csv(self, ruta_csv: str | Path) -> dict[str, int]:
        """Importa activos masivamente desde un archivo CSV."""
        importados = 0
        omitidos = 0
        with open(ruta_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.registrar_activo(
                        codigo=row["codigo"],
                        tipo=row["tipo"],
                        marca=row["marca"],
                        modelo=row["modelo"],
                        numero_serie=row["numero_serie"],
                        fecha_compra=row["fecha_compra"],
                        fecha_garantia=row.get("fecha_garantia") or row["fecha_compra"],
                        costo=float(row["costo"]),
                        estado=row.get("estado", "bodega"),
                    )
                    importados += 1
                except (ValueError, KeyError):
                    omitidos += 1
        return {"importados": importados, "omitidos": omitidos}

    def marcar_verificado_auditoria(
        self, codigo: str, verificado: bool = True
    ) -> Activo:
        """Marca un activo como verificado fisicamente durante auditoria."""
        usuario = obtener_usuario_linux()
        resultado: dict[str, Activo] = {}

        def _mutar(datos: dict[str, Any]) -> dict[str, Any]:
            activos = [Activo.from_dict(a) for a in datos.get("activos", [])]
            encontrado = next(
                (a for a in activos if a.codigo == codigo.strip().upper()), None
            )
            if not encontrado:
                raise ValueError(f"Activo {codigo} no encontrado.")
            encontrado.verificado_auditoria = verificado
            encontrado.historial.append(
                MovimientoHistorial(
                    fecha=_ahora_iso(),
                    accion="AUDITORIA",
                    empleado=encontrado.empleado_asignado or "N/A",
                    usuario_sistema=usuario,
                    detalle=f"Verificacion fisica = {verificado}",
                )
            )
            resultado["activo"] = encontrado
            datos["activos"] = [a.to_dict() for a in activos]
            return datos

        self.almacen.actualizar_datos(_mutar)
        return resultado["activo"]

    def listar_faltantes_auditoria(self) -> list[Activo]:
        """Lista activos activos (no dados de baja) sin verificacion fisica."""
        return [
            a
            for a in self.listar_activos()
            if a.estado != "baja" and not a.verificado_auditoria
        ]

    def detectar_series_duplicadas(self) -> dict[str, list[Activo]]:
        """Detecta numeros de serie repetidos en el inventario."""
        activos = self.listar_activos()
        conteo = Counter(a.numero_serie.strip().lower() for a in activos)
        duplicados: dict[str, list[Activo]] = {}
        for serie_lower, cantidad in conteo.items():
            if cantidad > 1:
                coincidencias = [
                    a for a in activos if a.numero_serie.strip().lower() == serie_lower
                ]
                duplicados[coincidencias[0].numero_serie] = coincidencias
        return duplicados
