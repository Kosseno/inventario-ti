# Sistema de Inventario de Activos de TI (Terminal / Linux)

**Caso Practico 4 — Programacion de Sistemas Abiertos (UTH)**  
**Equipo 4** | Docente: Ing. Arvin Rodas

## 1. Problema que resuelve
Una empresa de desarrollo de software con 120 empleados enfrenta perdidas de trazabilidad sobre sus laptops, monitores, servidores y licencias de software: en la ultima auditoria no fue posible determinar quien tenia asignado cada equipo y se pagaron licencias excedidas.

Este sistema de terminal construido en **Python** con **`curses`** sobre **Linux** centraliza el ciclo de vida del hardware y software con bloqueo concurrente para sesiones SSH simultaneas, auditoria automatica por usuario de Linux y reportes programados mediante `cron`.

## 2. Caracteristicas implementadas
- **Gestion de activos:** Registro, edicion y baja con estados (`en uso`, `bodega`, `reparacion`, `baja`).
- **Trazabilidad y auditoria:** Historial completo de asignaciones y devoluciones registrando fecha y usuario real de Linux (`os.getuid()` y `pwd.getpwuid()`).
- **Concurrencia segura:** Bloqueo exclusivo de archivo mediante `fcntl.flock()` y escritura atomica para evitar corrupcion ante multiples tecnicos conectados por SSH.
- **Control de garantias y licencias:** Alertas de garantias por vencer en <= 30 dias y deteccion de licencias con puestos asignados mayores a los comprados.
- **Consultas y reportes:** Busqueda por serie/tipo, vista *"Que tiene asignado este empleado?"* y calculo de depreciacion lineal exportable a CSV.
- **Funciones de auditoria:** Importacion masiva desde CSV, verificacion fisica de inventario y deteccion de numeros de serie duplicados.
