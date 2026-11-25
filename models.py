"""Modelos de datos para el sistema de inventario de activos de TI."""

from dataclasses import asdict, dataclass, field
from typing import Any

ESTADOS_VALIDOS = ("en uso", "bodega", "reparacion", "baja")


@dataclass
class MovimientoHistorial:
    """Registro inmutable de movimientos sobre un activo."""

    fecha: str
    accion: str
    empleado: str
    usuario_sistema: str
    detalle: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MovimientoHistorial":
        return cls(**data)


@dataclass
class Activo:
    """Representa un activo fisico de hardware o infraestructura."""

    codigo: str
    tipo: str
    marca: str
    modelo: str
    numero_serie: str
    fecha_compra: str  # Formato YYYY-MM-DD
    fecha_garantia: str  # Formato YYYY-MM-DD
    costo: float
    estado: str = "bodega"
    empleado_asignado: str | None = None
    verificado_auditoria: bool = False
    historial: list[MovimientoHistorial] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["historial"] = [m.to_dict() for m in self.historial]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Activo":
        historial_raw = data.get("historial", [])
        historial = [MovimientoHistorial.from_dict(m) for m in historial_raw]
        return cls(
            codigo=data["codigo"],
            tipo=data["tipo"],
            marca=data["marca"],
            modelo=data["modelo"],
            numero_serie=data["numero_serie"],
            fecha_compra=data["fecha_compra"],
            fecha_garantia=data.get("fecha_garantia", data["fecha_compra"]),
            costo=float(data["costo"]),
            estado=data.get("estado", "bodega"),
            empleado_asignado=data.get("empleado_asignado"),
            verificado_auditoria=bool(data.get("verificado_auditoria", False)),
            historial=historial,
        )


@dataclass
class Licencia:
    """Control de licencias de software por puestos."""

    codigo: str
    software: str
    puestos_comprados: int
    fecha_vencimiento: str  # Formato YYYY-MM-DD
    costo_unitario: float = 0.0
    empleados_asignados: list[str] = field(default_factory=list)

    @property
    def puestos_asignados(self) -> int:
        return len(self.empleados_asignados)

    @property
    def excedida(self) -> bool:
        return self.puestos_asignados > self.puestos_comprados

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Licencia":
        return cls(
            codigo=data["codigo"],
            software=data["software"],
            puestos_comprados=int(data["puestos_comprados"]),
            fecha_vencimiento=data["fecha_vencimiento"],
            costo_unitario=float(data.get("costo_unitario", 0.0)),
            empleados_asignados=list(data.get("empleados_asignados", [])),
        )
