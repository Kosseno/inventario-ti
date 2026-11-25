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

## 3. Automatizacion de alertas con Cron (`--alertas`)
El modo sin interfaz grafica genera `data/alertas_cron.txt` con garantias proximas a vencer y licencias excedidas sin inicializar `curses`:

```bash
python3 inventario.py --alertas

Para programarlo automaticamente todos los lunes a las 8:00 AM, abre el programador de tareas con `crontab -e` y agrega la siguiente linea ajustando la ruta de tu servidor:
```cron
0 8 \* \* 1 cd /home/jasson/inventario-ti \&\& /usr/bin/python3 inventario.py --alertas
```
4. Instalacion y configuracion del entorno
Requisitos previos (Ubuntu / WSL2)
Sistema operativo: Linux (Ubuntu Server, Ubuntu Desktop o WSL2 en Windows).
Python: Version 3.10 o superior (el programa utiliza unicamente la libreria estandar de Python).
Paquetes del sistema: `git` y `python3-venv` para crear el entorno virtual aislado.
Pasos de instalacion
Instalar dependencias base en Ubuntu/Debian:
```bash
   sudo apt update \&\& sudo apt install -y python3 python3-venv git
   ```
Clonar el repositorio y entrar al directorio:
```bash
   git clone https://github.com/Kosseno/inventario-ti.git
   cd inventario-ti
   ```
Crear y activar el entorno virtual:
```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
Instalar las herramientas de desarrollo (`pytest` y `ruff`):
```bash
   pip install -r requirements.txt
   ```
Asignar permisos de ejecucion al script de arranque:
```bash
   chmod +x run.sh
   ```
5. Como arrancar el sistema
El sistema puede iniciarse mediante cualquiera de los siguientes comandos desde la raiz del proyecto:
Usando el script de arranque:
```bash
  ./run.sh
  ```
Ejecutando directamente con Python:
```bash
  python3 main.py
  ```
(Tambien funciona con `python3 inventario.py`).
La aplicacion inicia protegida con `curses.wrapper()`, garantizando que la terminal recupere su estado y cursor normal al salir con `q` o ante cualquier interrupcion.
6. Guia de uso
Controles generales de la interfaz
Flechas `Arriba` / `Abajo`: Desplazarse por las opciones del menu principal.
`Enter`: Ingresar al modulo seleccionado o confirmar datos en formularios.
`q` / `ESC`: Regresar al menu anterior o salir del sistema de forma segura.
Redimensionado (`KEY\_RESIZE`): Las ventanas (`curses.newwin`) se adaptan automaticamente si cambia el tamano de la ventana de terminal (tamano minimo recomendado: `62x16`).
Modulos disponibles
Opcion	Modulo	Acciones y atajos principales
1	Activos	`\[R]` Registrar equipo, `\[E]` Editar ficha completa, `\[B]` Dar de baja.
2	Asignaciones	`\[A]` Asignar a empleado, `\[D]` Devolver a bodega/reparacion, `\[H]` Ver historial auditable.
3	Licencias	`\[N]` Registrar software, `\[A]` Asignar puesto (alerta si excede), `\[X]` Revocar puesto.
4	Busquedas	`\[1]` Buscar por numero de serie, `\[2]` Buscar por tipo, `\[3]` Vista "Que tiene este empleado?".
5	Reportes	Visualiza garantias por vencer (<= 30 dias), depreciacion lineal a 4 anos y `\[X]` Exportar a CSV.
6	Auditoria	`\[V]` Marcar verificacion fisica, `\[I]` Importar activos desde CSV, `\[S]` Detectar series duplicadas.
Capturas de pantalla / Demostracion
(Agregar aqui las capturas de pantalla del menu principal, vista por empleado y reporte de alertas, o el enlace de grabacion con `asciinema`).
7. Pruebas automaticas y calidad de codigo
Con el entorno virtual activado (`source .venv/bin/activate`), ejecuta las validaciones de calidad y la suite de 12 pruebas unitarias sobre la logica de negocio:
```bash
ruff check .
pytest -v
```
8. Estructura del proyecto
```text
inventario-ti/
├── data/                     # Almacenamiento JSON, reportes CSV y alertas de cron
├── tests/
│   └── test\_inventario.py    # 12 pruebas unitarias de logica con pytest
├── inventario.py             # Punto de entrada CLI (--alertas y curses.wrapper)
├── main.py                   # Alias de arranque principal
├── models.py                 # Modelos de datos (Activo, Licencia, MovimientoHistorial)
├── pyproject.toml            # Configuracion de ruff y pytest
├── requirements.txt          # Herramientas de desarrollo (pytest, ruff)
├── run.sh                    # Script ejecutable de arranque en Linux
├── services.py               # Logica de negocio, depreciacion, CSV y auditoria
├── storage.py                # Persistencia JSON con fcntl.flock y os.getuid/pwd
└── tui.py                    # Interfaz de terminal interactiva en curses
```
