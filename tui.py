"""Interfaz de usuario en terminal (TUI) construida con el modulo curses."""

import curses

from services import InventarioService

MENU_OPCIONES = [
    "1. Listar / Registrar / Editar / Baja de Activos",
    "2. Asignar / Devolver Activos e Historial",
    "3. Control de Licencias de Software",
    "4. Busqueda y Vista: Que tiene este empleado?",
    "5. Alertas de Garantias (30 dias) y Depreciacion Lineal",
    "6. Auditoria Fisica, Importar CSV y Series Duplicadas",
    "7. Salir (q)",
]


def _init_colores() -> None:
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)  # Titulos
        curses.init_pair(2, curses.COLOR_GREEN, -1)  # OK / Disponible
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Advertencia / En uso
        curses.init_pair(4, curses.COLOR_RED, -1)  # Alerta / Baja / Exceso
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)  # Seleccion


def _escribir_seguro(
    win: curses.window, y: int, x: int, texto: str, attr: int = 0
) -> None:
    """Evita curses.error si la terminal es estrecha."""
    max_y, max_x = win.getmaxyx()
    if 0 <= y < max_y and 0 <= x < max_x - 1:
        recorte = texto[: max_x - x - 1]
        try:
            win.addstr(y, x, recorte, attr)
        except curses.error:
            pass


def _pedir_input(
    win: curses.window, y: int, x: int, prompt: str, default: str = ""
) -> str | None:
    """Lee texto del usuario; retorna None si presiona ESC."""
    _escribir_seguro(win, y, x, prompt, curses.color_pair(1))
    win.refresh()
    curses.echo()
    curses.curs_set(1)
    try:
        max_y, max_x = win.getmaxyx()
        ancho = max(10, max_x - (x + len(prompt)) - 2)
        raw = win.getstr(y, x + len(prompt), ancho)
        texto = raw.decode("utf-8", errors="ignore").strip()
        return texto if texto else default
    except curses.error:
        return default
    finally:
        curses.noecho()
        curses.curs_set(0)


def _pausa_mensaje(stdscr: curses.window, mensaje: str, color: int = 2) -> None:
    max_y, max_x = stdscr.getmaxyx()
    win = curses.newwin(5, max(40, max_x - 4), max(2, max_y // 2 - 2), 2)
    win.box()
    _escribir_seguro(win, 1, 2, mensaje, curses.color_pair(color) | curses.A_BOLD)
    _escribir_seguro(win, 3, 2, "Presione cualquier tecla para continuar...")
    win.refresh()
    win.getch()


def _pantalla_activos(stdscr: curses.window, servicio: InventarioService) -> None:
    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        if max_y < 16 or max_x < 60:
            _escribir_seguro(stdscr, 0, 0, "Amplie la terminal (min. 60x16)...")
            stdscr.refresh()
            if stdscr.getch() == ord("q"):
                return
            continue

        win = curses.newwin(max_y - 2, max_x - 2, 1, 1)
        win.box()
        _escribir_seguro(
            win, 1, 2, "GESTION DE ACTIVOS DE TI", curses.color_pair(1) | curses.A_BOLD
        )
        _escribir_seguro(
            win,
            2,
            2,
            "[R] Registrar  [E] Editar  [B] Dar de baja  [Q] Volver",
            curses.color_pair(3),
        )

        activos = servicio.listar_activos()
        _escribir_seguro(
            win,
            4,
            2,
            (
                f"{'CODIGO':<9} {'TIPO':<11} {'MARCA/MODELO':<20} "
                f"{'SERIE':<14} {'ESTADO':<11} {'ASIGNADO'}"
            ),
            curses.A_BOLD,
        )
        for idx, act in enumerate(activos[: max_y - 9]):
            color = 2 if act.estado == "bodega" else (4 if act.estado == "baja" else 3)
            linea = (
                f"{act.codigo:<9} {act.tipo:<11} "
                f"{(act.marca + ' ' + act.modelo)[:19]:<20} "
                f"{act.numero_serie[:13]:<14} {act.estado:<11} "
                f"{act.empleado_asignado or '-'}"
            )
            _escribir_seguro(win, 5 + idx, 2, linea, curses.color_pair(color))

        stdscr.refresh()
        win.refresh()
        tecla = win.getch()

        if tecla == curses.KEY_RESIZE:
            continue
        if tecla in (ord("q"), ord("Q"), 27):
            return
        if tecla in (ord("r"), ord("R")):
            form = curses.newwin(13, max_x - 6, 3, 3)
            form.box()
            _escribir_seguro(form, 1, 2, "NUEVO ACTIVO", curses.color_pair(1))
            try:
                cod = _pedir_input(form, 2, 2, "Codigo (ej. ACT-010): ") or ""
                tipo = _pedir_input(form, 3, 2, "Tipo (Laptop/Monitor): ") or ""
                marca = _pedir_input(form, 4, 2, "Marca: ") or ""
                modelo = _pedir_input(form, 5, 2, "Modelo: ") or ""
                serie = _pedir_input(form, 6, 2, "Numero de serie: ") or ""
                f_comp = _pedir_input(form, 7, 2, "Fecha compra (YYYY-MM-DD): ") or ""
                f_gar = (
                    _pedir_input(form, 8, 2, "Fin garantia (YYYY-MM-DD): ") or f_comp
                )
                costo = float(_pedir_input(form, 9, 2, "Costo USD: ", "0") or "0")
                servicio.registrar_activo(
                    cod, tipo, marca, modelo, serie, f_comp, costo, "bodega", f_gar
                )
                _pausa_mensaje(stdscr, f"Activo {cod.upper()} registrado con exito.", 2)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)
        elif tecla in (ord("e"), ord("E")):
            form = curses.newwin(13, max_x - 6, 2, 3)
            form.box()
            _escribir_seguro(
                form,
                1,
                2,
                "EDITAR ACTIVO (Enter = mantener valor actual)",
                curses.color_pair(1),
            )
            try:
                cod = _pedir_input(form, 2, 2, "Codigo de activo a editar: ") or ""
                actual = servicio.obtener_activo(cod)
                if not actual:
                    raise ValueError(f"Activo {cod} no encontrado.")
                tipo = _pedir_input(form, 3, 2, f"Tipo [{actual.tipo}]: ") or None
                marca = _pedir_input(form, 4, 2, f"Marca [{actual.marca}]: ") or None
                modelo = _pedir_input(form, 5, 2, f"Modelo [{actual.modelo}]: ") or None
                serie = (
                    _pedir_input(form, 6, 2, f"Serie [{actual.numero_serie}]: ") or None
                )
                f_comp = (
                    _pedir_input(form, 7, 2, f"Compra [{actual.fecha_compra}]: ")
                    or None
                )
                f_gar = (
                    _pedir_input(form, 8, 2, f"Garantia [{actual.fecha_garantia}]: ")
                    or None
                )
                costo_str = _pedir_input(form, 9, 2, f"Costo [{actual.costo}]: ") or ""
                costo = float(costo_str) if costo_str else None
                est = (
                    _pedir_input(
                        form,
                        10,
                        2,
                        f"Estado [{actual.estado}] (en uso/bodega/reparacion/baja): ",
                    )
                    or None
                )
                servicio.editar_activo(
                    cod,
                    tipo=tipo,
                    marca=marca,
                    modelo=modelo,
                    numero_serie=serie,
                    fecha_compra=f_comp,
                    fecha_garantia=f_gar,
                    costo=costo,
                    estado=est,
                )
                _pausa_mensaje(stdscr, f"Activo {actual.codigo} actualizado.", 2)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)
        elif tecla in (ord("b"), ord("B")):
            form = curses.newwin(7, max_x - 6, 4, 3)
            form.box()
            try:
                cod = _pedir_input(form, 1, 2, "Codigo de activo para BAJA: ") or ""
                mot = (
                    _pedir_input(form, 2, 2, "Motivo de baja: ", "Obsolescencia") or ""
                )
                servicio.dar_de_baja_activo(cod, mot)
                _pausa_mensaje(stdscr, f"Activo {cod.upper()} dado de baja.", 3)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)


def _pantalla_asignaciones(stdscr: curses.window, servicio: InventarioService) -> None:
    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        win = curses.newwin(max_y - 2, max_x - 2, 1, 1)
        win.box()
        _escribir_seguro(
            win,
            1,
            2,
            "ASIGNACIONES, DEVOLUCIONES E HISTORIAL",
            curses.color_pair(1) | curses.A_BOLD,
        )
        _escribir_seguro(
            win,
            2,
            2,
            "[A] Asignar equipo  [D] Devolver equipo  [H] Ver historial  [Q] Volver",
            curses.color_pair(3),
        )

        activos = servicio.listar_activos()
        for idx, act in enumerate(activos[: max_y - 8]):
            linea = (
                f"{act.codigo:<9} | {act.tipo:<10} | Estado: {act.estado:<10} | "
                f"Empleado: {act.empleado_asignado or 'DISPONIBLE'}"
            )
            _escribir_seguro(win, 4 + idx, 2, linea)

        stdscr.refresh()
        win.refresh()
        tecla = win.getch()
        if tecla == curses.KEY_RESIZE:
            continue
        if tecla in (ord("q"), ord("Q"), 27):
            return
        if tecla in (ord("a"), ord("A")):
            form = curses.newwin(7, max_x - 6, 4, 3)
            form.box()
            try:
                cod = _pedir_input(form, 1, 2, "Codigo del activo: ") or ""
                emp = _pedir_input(form, 2, 2, "Nombre del empleado: ") or ""
                servicio.asignar_activo(cod, emp)
                _pausa_mensaje(stdscr, f"Asignado a {emp} (auditoria registrada).", 2)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)
        elif tecla in (ord("d"), ord("D")):
            form = curses.newwin(8, max_x - 6, 4, 3)
            form.box()
            try:
                cod = _pedir_input(form, 1, 2, "Codigo del activo a devolver: ") or ""
                dest = (
                    _pedir_input(form, 2, 2, "Destino (bodega/reparacion): ", "bodega")
                    or "bodega"
                )
                servicio.devolver_activo(cod, dest)
                _pausa_mensaje(stdscr, "Devolucion registrada con exito.", 2)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)
        elif tecla in (ord("h"), ord("H")):
            form = curses.newwin(max_y - 6, max_x - 6, 3, 3)
            form.box()
            cod = _pedir_input(form, 1, 2, "Codigo de activo: ") or ""
            activo = servicio.obtener_activo(cod)
            if not activo:
                _pausa_mensaje(stdscr, "Activo no encontrado.", 4)
            else:
                for i, mov in enumerate(activo.historial[-(max_y - 11) :]):
                    _escribir_seguro(
                        form,
                        3 + i,
                        2,
                        f"[{mov.fecha}] {mov.accion} | Emp: {mov.empleado} | "
                        f"LinuxUser: {mov.usuario_sistema} | {mov.detalle}",
                    )
                _escribir_seguro(
                    form, max_y - 8, 2, "Presione una tecla para cerrar..."
                )
                form.refresh()
                form.getch()


def _pantalla_licencias(stdscr: curses.window, servicio: InventarioService) -> None:
    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        win = curses.newwin(max_y - 2, max_x - 2, 1, 1)
        win.box()
        _escribir_seguro(
            win,
            1,
            2,
            "CONTROL DE LICENCIAS DE SOFTWARE",
            curses.color_pair(1) | curses.A_BOLD,
        )
        _escribir_seguro(
            win,
            2,
            2,
            "[N] Nueva licencia  [A] Asignar puesto  [X] Revocar puesto  [Q] Volver",
            curses.color_pair(3),
        )

        licencias = servicio.listar_licencias()
        for idx, lic in enumerate(licencias[: max_y - 8]):
            alerta = " EXCEDIDA!" if lic.excedida else " OK"
            color = 4 if lic.excedida else 2
            linea = (
                f"{lic.codigo:<8} | {lic.software:<20} | "
                f"Puestos: {lic.puestos_asignados}/{lic.puestos_comprados}{alerta} | "
                f"Usuarios: {', '.join(lic.empleados_asignados) or '-'}"
            )
            _escribir_seguro(win, 4 + idx, 2, linea, curses.color_pair(color))

        stdscr.refresh()
        win.refresh()
        tecla = win.getch()
        if tecla == curses.KEY_RESIZE:
            continue
        if tecla in (ord("q"), ord("Q"), 27):
            return
        if tecla in (ord("n"), ord("N")):
            form = curses.newwin(9, max_x - 6, 4, 3)
            form.box()
            try:
                cod = _pedir_input(form, 1, 2, "Codigo licencia (LIC-01): ") or ""
                soft = _pedir_input(form, 2, 2, "Software: ") or ""
                puestos = int(
                    _pedir_input(form, 3, 2, "Puestos comprados: ", "1") or "1"
                )
                venc = _pedir_input(form, 4, 2, "Vencimiento (YYYY-MM-DD): ") or ""
                servicio.registrar_licencia(cod, soft, puestos, venc)
                _pausa_mensaje(stdscr, "Licencia registrada.", 2)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)
        elif tecla in (ord("a"), ord("A")):
            form = curses.newwin(7, max_x - 6, 4, 3)
            form.box()
            try:
                cod = _pedir_input(form, 1, 2, "Codigo licencia: ") or ""
                emp = _pedir_input(form, 2, 2, "Empleado: ") or ""
                lic = servicio.asignar_licencia(cod, emp)
                if lic.excedida:
                    _pausa_mensaje(
                        stdscr,
                        f"AVISO: Licencia {lic.software} EXCEDIDA "
                        f"({lic.puestos_asignados}/{lic.puestos_comprados}).",
                        4,
                    )
                else:
                    _pausa_mensaje(stdscr, "Puesto asignado correctamente.", 2)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)
        elif tecla in (ord("x"), ord("X")):
            form = curses.newwin(7, max_x - 6, 4, 3)
            form.box()
            try:
                cod = _pedir_input(form, 1, 2, "Codigo licencia: ") or ""
                emp = _pedir_input(form, 2, 2, "Empleado a revocar: ") or ""
                servicio.revocar_licencia(cod, emp)
                _pausa_mensaje(stdscr, "Puesto revocado.", 2)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)


def _pantalla_busqueda(stdscr: curses.window, servicio: InventarioService) -> None:
    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        win = curses.newwin(max_y - 2, max_x - 2, 1, 1)
        win.box()
        _escribir_seguro(
            win,
            1,
            2,
            "BUSQUEDA Y VISTA POR EMPLEADO",
            curses.color_pair(1) | curses.A_BOLD,
        )
        _escribir_seguro(
            win,
            2,
            2,
            (
                "[1] Buscar por Serie  [2] Buscar por Tipo  "
                "[3] Que tiene este empleado?  [Q] Volver"
            ),
            curses.color_pair(3),
        )
        stdscr.refresh()
        win.refresh()
        tecla = win.getch()
        if tecla == curses.KEY_RESIZE:
            continue
        if tecla in (ord("q"), ord("Q"), 27):
            return
        if tecla in (ord("1"), ord("2")):
            criterio = "serie" if tecla == ord("1") else "tipo"
            val = _pedir_input(win, 4, 2, f"Ingrese {criterio} a buscar: ") or ""
            resultados = servicio.buscar_activos(criterio, val)
            for idx, act in enumerate(resultados[: max_y - 10]):
                _escribir_seguro(
                    win,
                    6 + idx,
                    2,
                    f"{act.codigo} | {act.tipo} {act.marca} {act.modelo} | "
                    f"S/N: {act.numero_serie} | Asig: {act.empleado_asignado or '-'}",
                )
            _escribir_seguro(win, max_y - 4, 2, "Presione una tecla para continuar...")
            win.refresh()
            win.getch()
        elif tecla == ord("3"):
            emp = _pedir_input(win, 4, 2, "Nombre del empleado: ") or ""
            ficha = servicio.consultar_empleado(emp)
            _escribir_seguro(
                win,
                6,
                2,
                f"EQUIPOS ASIGNADOS ({len(ficha['activos'])}):",
                curses.color_pair(2) | curses.A_BOLD,
            )
            fila = 7
            for act in ficha["activos"]:
                _escribir_seguro(
                    win,
                    fila,
                    4,
                    (
                        f"- {act.codigo}: {act.tipo} {act.marca} "
                        f"{act.modelo} (S/N: {act.numero_serie})"
                    ),
                )
                fila += 1
            _escribir_seguro(
                win,
                fila + 1,
                2,
                f"LICENCIAS ASIGNADAS ({len(ficha['licencias'])}):",
                curses.color_pair(2) | curses.A_BOLD,
            )
            fila += 2
            for lic in ficha["licencias"]:
                _escribir_seguro(win, fila, 4, f"- {lic.codigo}: {lic.software}")
                fila += 1
            _escribir_seguro(win, max_y - 4, 2, "Presione una tecla para continuar...")
            win.refresh()
            win.getch()


def _pantalla_reportes(stdscr: curses.window, servicio: InventarioService) -> None:
    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        win = curses.newwin(max_y - 2, max_x - 2, 1, 1)
        win.box()
        _escribir_seguro(
            win,
            1,
            2,
            "GARANTIAS POR VENCER (30 DIAS) Y DEPRECIACION LINEAL",
            curses.color_pair(1) | curses.A_BOLD,
        )
        _escribir_seguro(
            win,
            2,
            2,
            "[X] Exportar depreciacion a CSV  [Q] Volver",
            curses.color_pair(3),
        )

        alertas = servicio.alertas_garantias(30)
        _escribir_seguro(
            win, 4, 2, f"ALERTAS DE GARANTIA ({len(alertas)}):", curses.color_pair(4)
        )
        fila = 5
        for al in alertas[:5]:
            _escribir_seguro(
                win,
                fila,
                4,
                f"{al['codigo']} | {al['equipo']} | Vence: {al['fecha_garantia']} "
                f"({al['dias_restantes']} dias)",
                curses.color_pair(4),
            )
            fila += 1

        fila += 1
        _escribir_seguro(
            win,
            fila,
            2,
            "VALOR ACTUAL CON DEPRECIACION LINEAL (4 ANOS):",
            curses.A_BOLD,
        )
        fila += 1
        reporte = servicio.calcular_depreciacion_lineal(vida_util_anios=4)
        for item in reporte[: max(1, max_y - fila - 4)]:
            _escribir_seguro(
                win,
                fila,
                4,
                f"{item['codigo']} | {item['marca_modelo'][:20]:<20} | "
                f"Orig: ${item['costo_original']:>8.2f} | "
                f"Actual: ${item['valor_actual']:>8.2f} ({item['estado']})",
            )
            fila += 1

        stdscr.refresh()
        win.refresh()
        tecla = win.getch()
        if tecla == curses.KEY_RESIZE:
            continue
        if tecla in (ord("q"), ord("Q"), 27):
            return
        if tecla in (ord("x"), ord("X")):
            ruta = servicio.exportar_reporte_depreciacion()
            _pausa_mensaje(stdscr, f"Reporte exportado a: {ruta}", 2)


def _pantalla_auditoria(stdscr: curses.window, servicio: InventarioService) -> None:
    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        win = curses.newwin(max_y - 2, max_x - 2, 1, 1)
        win.box()
        _escribir_seguro(
            win,
            1,
            2,
            "HERRAMIENTAS DE AUDITORIA Y CARGA MASIVA",
            curses.color_pair(1) | curses.A_BOLD,
        )
        _escribir_seguro(
            win,
            2,
            2,
            (
                "[V] Verificar activo fisico  [I] Importar CSV  "
                "[S] Series duplicadas  [Q] Volver"
            ),
            curses.color_pair(3),
        )

        faltantes = servicio.listar_faltantes_auditoria()
        _escribir_seguro(
            win, 4, 2, f"ACTIVOS PENDIENTES DE VERIFICACION FISICA ({len(faltantes)}):"
        )
        for idx, act in enumerate(faltantes[: max_y - 9]):
            _escribir_seguro(
                win,
                5 + idx,
                4,
                (
                    f"{act.codigo} | {act.tipo} {act.marca} {act.modelo} | "
                    f"S/N: {act.numero_serie} | "
                    f"Ubicacion/Emp: {act.empleado_asignado or act.estado}"
                ),
            )

        stdscr.refresh()
        win.refresh()
        tecla = win.getch()
        if tecla == curses.KEY_RESIZE:
            continue
        if tecla in (ord("q"), ord("Q"), 27):
            return
        if tecla in (ord("v"), ord("V")):
            cod = (
                _pedir_input(win, max_y - 4, 2, "Codigo verificado fisicamente: ") or ""
            )
            try:
                servicio.marcar_verificado_auditoria(cod, True)
                _pausa_mensaje(stdscr, f"{cod.upper()} marcado como verificado.", 2)
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error: {err}", 4)
        elif tecla in (ord("i"), ord("I")):
            ruta = (
                _pedir_input(win, max_y - 4, 2, "Ruta del CSV: ", "data/importar.csv")
                or ""
            )
            try:
                res = servicio.importar_csv(ruta)
                _pausa_mensaje(
                    stdscr,
                    f"Importados: {res['importados']} | Omitidos: {res['omitidos']}",
                    2,
                )
            except Exception as err:
                _pausa_mensaje(stdscr, f"Error leyendo CSV: {err}", 4)
        elif tecla in (ord("s"), ord("S")):
            dups = servicio.detectar_series_duplicadas()
            if not dups:
                _pausa_mensaje(
                    stdscr, "No se encontraron numeros de serie duplicados.", 2
                )
            else:
                detalle = ", ".join(
                    f"{sn} ({len(lista)} equipos)" for sn, lista in dups.items()
                )
                _pausa_mensaje(stdscr, f"Duplicados detectados: {detalle}", 4)


def ejecutar_tui(stdscr: curses.window, servicio: InventarioService) -> None:
    """Bucle principal de la interfaz curses."""
    curses.curs_set(0)
    stdscr.keypad(True)
    _init_colores()
    indice = 0

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        if max_y < 16 or max_x < 62:
            _escribir_seguro(
                stdscr,
                0,
                0,
                "Terminal muy pequena. Redimensione al menos a 62x16 o presione 'q'.",
                curses.color_pair(4),
            )
            stdscr.refresh()
            tecla = stdscr.getch()
            if tecla in (ord("q"), ord("Q")):
                return
            continue

        # Ventana superior (cabecera)
        header = curses.newwin(3, max_x - 2, 1, 1)
        header.box()
        _escribir_seguro(
            header,
            1,
            2,
            "SISTEMA DE INVENTARIO DE ACTIVOS DE TI - UTH (Linux/curses)",
            curses.color_pair(1) | curses.A_BOLD,
        )

        # Ventana central (menu)
        body = curses.newwin(max_y - 7, max_x - 2, 4, 1)
        body.box()
        _escribir_seguro(
            body, 1, 2, "Use Arriba/Abajo y ENTER para seleccionar:", curses.A_BOLD
        )
        for i, opcion in enumerate(MENU_OPCIONES):
            estilo = curses.color_pair(5) if i == indice else curses.A_NORMAL
            _escribir_seguro(body, 3 + i, 4, f" {opcion} ", estilo)

        # Ventana inferior (estado)
        footer = curses.newwin(3, max_x - 2, max_y - 3, 1)
        footer.box()
        activos = servicio.listar_activos()
        alertas = servicio.alertas_garantias(30)
        excedidas = servicio.licencias_excedidas()
        resumen = (
            f"Activos: {len(activos)} | Garantias <=30d: {len(alertas)} | "
            f"Licencias excedidas: {len(excedidas)} | [q] Salir"
        )
        _escribir_seguro(footer, 1, 2, resumen, curses.color_pair(2))

        stdscr.refresh()
        header.refresh()
        body.refresh()
        footer.refresh()

        tecla = stdscr.getch()
        if tecla == curses.KEY_RESIZE:
            continue
        if tecla in (ord("q"), ord("Q")):
            return
        if tecla == curses.KEY_UP:
            indice = (indice - 1) % len(MENU_OPCIONES)
        elif tecla == curses.KEY_DOWN:
            indice = (indice + 1) % len(MENU_OPCIONES)
        elif tecla in (curses.KEY_ENTER, 10, 13):
            if indice == 0:
                _pantalla_activos(stdscr, servicio)
            elif indice == 1:
                _pantalla_asignaciones(stdscr, servicio)
            elif indice == 2:
                _pantalla_licencias(stdscr, servicio)
            elif indice == 3:
                _pantalla_busqueda(stdscr, servicio)
            elif indice == 4:
                _pantalla_reportes(stdscr, servicio)
            elif indice == 5:
                _pantalla_auditoria(stdscr, servicio)
            elif indice == 6:
                return
