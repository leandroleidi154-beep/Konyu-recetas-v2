import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# 1. Configuración de la página
st.set_page_config(
    page_title="Gestión de Recetas - Konyu", page_icon="💊", layout="wide"
)


# 2. Conexión a Supabase usando los secretos de Streamlit
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


supabase = init_connection()

# 3. Inicialización del estado de sesión
if "usuario_logueado" not in st.session_state:
    st.session_state["usuario_logueado"] = None


# --- CLASE PARA GENERACIÓN DE PDF ---
class PDFComprobante(FPDF):
    def __init__(self, sucursal, fecha_str, ref_lote):
        super().__init__()
        self.sucursal = sucursal
        self.fecha_str = fecha_str
        self.ref_lote = ref_lote

    def header(self):
        self.set_font("Arial", "B", 15)
        self.cell(0, 10, "Resumen de Cierre de Lote", 0, 1, "C")
        self.set_font("Arial", "B", 11)
        self.cell(
            0,
            6,
            f"Sucursal: {self.sucursal}  |  Fecha de Recetas: {self.fecha_str}",
            0,
            1,
            "C",
        )
        self.set_font("Arial", "I", 10)
        self.cell(0, 6, f"Referencia: {self.ref_lote}", 0, 1, "C")
        self.ln(4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")


def generar_pdf_bytes(
    sucursal, fecha_str, ref_lote, total_envio, total_vales, df_os_resumen, df_vales_det
):
    pdf = PDFComprobante(sucursal, fecha_str, ref_lote)
    pdf.add_page()

    # 1. Cuadro de Resumen por Obra Social
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "1. Resumen por Obra Social (Recetas Enviadas)", 0, 1, "L")
    pdf.ln(1)

    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 6, "Obra Social", 1, 0, "L", True)
    pdf.cell(30, 6, "Total CSV", 1, 0, "C", True)
    pdf.cell(30, 6, "Vales Retenidos", 1, 0, "C", True)
    pdf.cell(40, 6, "A Enviar (Fisico)", 1, 1, "C", True)

    pdf.set_font("Arial", "", 9)
    if not df_os_resumen.empty:
        for _, row_os in df_os_resumen.iterrows():
            os_txt = str(row_os["Obra Social"])[:45]
            pdf.cell(90, 6, os_txt, 1, 0, "L")
            pdf.cell(30, 6, str(row_os["Total"]), 1, 0, "C")
            pdf.cell(30, 6, str(row_os["Vales"]), 1, 0, "C")
            pdf.cell(40, 6, str(row_os["A Enviar"]), 1, 1, "C")
    else:
        pdf.cell(190, 6, "Detalle por obra social no disponible.", 1, 1, "C")

    pdf.ln(6)

    # 2. Cuadro de Vales Retenidos
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "2. Detalle de Vales Retenidos (Pendientes en Sucursal)", 0, 1, "L")
    pdf.ln(1)

    if not df_vales_det.empty:
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(60, 6, "Obra Social", 1, 0, "L", True)
        pdf.cell(45, 6, "Plan", 1, 0, "L", True)
        pdf.cell(42, 6, "Nro Ticket", 1, 0, "C", True)
        pdf.cell(43, 6, "T.T.", 1, 1, "C", True)

        pdf.set_font("Arial", "", 8)
        for _, row_v in df_vales_det.iterrows():
            pdf.cell(60, 6, str(row_v["Obra Social"])[:30], 1, 0, "L")
            pdf.cell(45, 6, str(row_v["Plan"])[:22], 1, 0, "L")
            pdf.cell(42, 6, str(row_v["Nro Ticket"]), 1, 0, "C")
            pdf.cell(43, 6, str(row_v["T.T"]), 1, 1, "C")
    else:
        pdf.set_font("Arial", "I", 9)
        pdf.cell(190, 6, "No se registraron vales retenidos en este lote.", 1, 1, "C")

    pdf.ln(6)

    # 3. Totales finales encuadrados
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(245, 245, 245)
    total_gral = total_envio + total_vales
    pdf.cell(
        190,
        8,
        f" TOTALES GENERALES:   Procesadas: {total_gral}  |  Enviadas: {total_envio}  |  Vales Retenidos: {total_vales}",
        1,
        1,
        "C",
        True,
    )

    return pdf.output(dest="S").encode("latin1")


# --- PANTALLA DE LOGIN ---
if st.session_state["usuario_logueado"] is None:
    st.title("💊 Konyu Recetas - Iniciar Sesión")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Acceso al Sistema")
        usuario_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password")

        if st.button("Ingresar", type="primary", use_container_width=True):
            if usuario_input and password_input:
                try:
                    res = (
                        supabase.table("usuarios")
                        .select("*")
                        .eq("nombre", usuario_input)
                        .eq("password", password_input)
                        .execute()
                    )

                    if res.data and len(res.data) > 0:
                        st.session_state["usuario_logueado"] = res.data[0]
                        st.success("¡Inicio de sesión exitoso!")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")
                except Exception as e:
                    st.error(f"Error de conexión con la base de datos: {e}")
            else:
                st.warning("Por favor, completá ambos campos.")

# --- PANEL PRINCIPAL (USUARIO LOGUEADO) ---
else:
    user = st.session_state["usuario_logueado"]
    st.sidebar.title("💊 Konyu Recetas")
    st.sidebar.write(f"**Usuario:** {user.get('nombre', 'Desconocido')}")
    st.sidebar.write(f"**Rol:** {user.get('rol', 'Sin Rol')}")

    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("---")

    rol = str(user.get("rol", "")).lower()

    # Vistas según el rol asignado
    if rol == "administrador":
        st.header("👑 Panel de Administrador - Gestión de Usuarios")

        tab1, tab2, tab3 = st.tabs(
            [
                "➕ Crear Nuevo Usuario",
                "📋 Listar / Modificar Usuarios",
                "📜 Historial de Lotes",
            ]
        )

        with tab1:
            st.subheader("Alta de Nuevo Usuario")
            with st.form("form_crear_usuario"):
                nuevo_nombre = st.text_input("Nombre de Usuario")
                nueva_pass = st.text_input("Contraseña", type="password")
                nuevo_rol = st.selectbox(
                    "Rol / Función", ["Sucursal", "Mutual", "Administrador"]
                )

                submitted = st.form_submit_button("Crear Usuario", type="primary")
                if submitted:
                    if nuevo_nombre and nueva_pass:
                        try:
                            supabase.table("usuarios").insert(
                                {
                                    "nombre": nuevo_nombre,
                                    "password": nueva_pass,
                                    "rol": nuevo_rol,
                                }
                            ).execute()
                            st.success(f"¡Usuario '{nuevo_nombre}' creado con éxito!")
                        except Exception as e:
                            st.error(f"Error al crear el usuario: {e}")
                    else:
                        st.warning("Completá todos los campos obligatorios.")

        with tab2:
            st.subheader("Usuarios Registrados en el Sistema")
            try:
                res_usuarios = (
                    supabase.table("usuarios").select("id, nombre, rol").execute()
                )
                usuarios_lista = res_usuarios.data

                if usuarios_lista:
                    for u in usuarios_lista:
                        with st.expander(f"👤 {u['nombre']} (Rol: {u['rol']})"):
                            col_a, col_b = st.columns(2)

                            with col_a:
                                with st.form(f"form_edit_{u['id']}"):
                                    st.write("Modificar datos")
                                    edit_pass = st.text_input(
                                        "Nueva Contraseña (opcional)",
                                        type="password",
                                        key=f"pass_{u['id']}",
                                    )
                                    edit_rol = st.selectbox(
                                        "Nuevo Rol",
                                        ["Sucursal", "Mutual", "Administrador"],
                                        index=(
                                            [
                                                "Sucursal",
                                                "Mutual",
                                                "Administrador",
                                            ].index(u["rol"])
                                            if u["rol"]
                                            in ["Sucursal", "Mutual", "Administrador"]
                                            else 0
                                        ),
                                        key=f"rol_{u['id']}",
                                    )

                                    if st.form_submit_button("Guardar Cambios"):
                                        try:
                                            update_data = {"rol": edit_rol}
                                            if edit_pass:
                                                update_data["password"] = edit_pass

                                            supabase.table("usuarios").update(
                                                update_data
                                            ).eq("id", u["id"]).execute()
                                            st.success(
                                                "¡Usuario actualizado correctamente!"
                                            )
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error al actualizar: {e}")

                            with col_b:
                                st.write("Zona de Peligro")
                                if u["nombre"] == user.get("nombre"):
                                    st.info(
                                        "No podés eliminar tu propia cuenta activa."
                                    )
                                else:
                                    if st.button(
                                        "🗑️ Eliminar Usuario", key=f"del_{u['id']}"
                                    ):
                                        try:
                                            supabase.table("usuarios").delete().eq(
                                                "id", u["id"]
                                            ).execute()
                                            st.success(
                                                f"Usuario {u['nombre']} eliminado."
                                            )
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error al eliminar: {e}")
                else:
                    st.info("No hay usuarios cargados en la base de datos.")
            except Exception as e:
                st.error(f"No se pudieron cargar los usuarios: {e}")

        with tab3:
            st.subheader("📋 Historial General de Lotes Guardados")
            try:
                res_lotes_admin = (
                    supabase.table("lotes")
                    .select("*")
                    .order("created_at", desc=True)
                    .execute()
                )
                if res_lotes_admin.data:
                    df_h_admin = pd.DataFrame(res_lotes_admin.data)
                    st.dataframe(
                        df_h_admin[
                            [
                                "id_lote",
                                "sucursal",
                                "fecha_carga",
                                "estado",
                                "observacion",
                                "created_at",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Aún no se han registrado lotes en la base de datos.")
            except Exception as e:
                st.error(f"Error al recuperar el historial: {e}")

    elif rol == "sucursal":
        st.header("🏪 Panel de Sucursal - Control y Generación de Lotes")

        tab_cierre, tab_historial = st.tabs(
            ["🔒 Cierre de Lote", "📜 Historial de Lotes"]
        )

        with tab_cierre:
            # Si ya se generó un lote con éxito
            if "lote_generado_exito" in st.session_state:
                lote_info = st.session_state["lote_generado_exito"]
                st.success(
                    f"¡Lote del día **{lote_info['fecha']}** guardado y cerrado con éxito en Supabase!"
                )
                st.markdown("---")
                st.subheader("📄 Resumen y Comprobante para Mutuales")
                st.info(
                    f"Resumen: {lote_info['total_envio']} recetas enviadas a mutuales | {lote_info['total_vales']} recetas retenidas como vales."
                )

                pdf_bytes = generar_pdf_bytes(
                    user.get("nombre", "Sucursal"),
                    lote_info["fecha"],
                    lote_info["referencia"],
                    lote_info["total_envio"],
                    lote_info["total_vales"],
                    lote_info.get("resumen_os", pd.DataFrame()),
                    lote_info.get("df_vales", pd.DataFrame()),
                )

                st.download_button(
                    label="📥 Descargar Resumen en PDF",
                    data=pdf_bytes,
                    file_name=f"Resumen_Lote_{lote_info['fecha'].replace('/', '-')}.pdf",
                    mime="application/pdf",
                    type="primary",
                )

                st.markdown("---")
                if st.button("➕ Cargar un nuevo lote o archivo", type="secondary"):
                    u_actual = st.session_state.get("usuario_logueado")
                    st.session_state.clear()
                    st.session_state["usuario_logueado"] = u_actual
                    st.rerun()
            else:
                # PASO 1: SELECCIÓN DE FECHA Y COMPROBACIÓN DE LOTE PREVIO
                st.subheader("1️⃣ Paso 1: Seleccioná la Fecha de las Recetas")

                col_fecha, col_reset = st.columns([3, 1])
                with col_fecha:
                    fecha_recetas = st.date_input(
                        "📅 Fecha correspondiente a las recetas"
                    )
                with col_reset:
                    st.write("")
                    st.write("")
                    if st.button(
                        "🔄 Reiniciar Datos",
                        help="Limpia la selección de vales y restablece los valores",
                    ):
                        u_actual = st.session_state.get("usuario_logueado")
                        st.session_state.clear()
                        st.session_state["usuario_logueado"] = u_actual
                        st.rerun()

                fecha_str_db = fecha_recetas.strftime("%Y-%m-%d")
                fecha_str_fmt = fecha_recetas.strftime("%d/%m/%Y")
                sucursal_actual = user.get("nombre", "Sucursal")

                lote_existente = None
                try:
                    res_check = (
                        supabase.table("lotes")
                        .select("*")
                        .eq("sucursal", sucursal_actual)
                        .eq("fecha_carga", fecha_str_db)
                        .execute()
                    )

                    if res_check.data and len(res_check.data) > 0:
                        lote_existente = res_check.data[0]
                except Exception as e:
                    pass

                if lote_existente:
                    st.warning(
                        f"⚠️ **ATENCIÓN:** Ya existe un lote registrado para la sucursal **{sucursal_actual}** con la fecha **{fecha_str_fmt}**."
                    )
                    st.info(
                        f"**Identificador previo:** `{lote_existente.get('id_lote')}` | **Observación:** {lote_existente.get('observacion')}"
                    )

                    col_eliminar, col_seguir = st.columns(2)
                    with col_eliminar:
                        if st.button(
                            "🗑️ Eliminar Lote Existente y Continuar", type="secondary"
                        ):
                            try:
                                supabase.table("lotes").delete().eq(
                                    "id_lote", lote_existente.get("id_lote")
                                ).execute()
                                st.success(
                                    "¡Lote anterior eliminado con éxito! Ya podés continuar cargando."
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al eliminar el lote: {e}")
                    with col_seguir:
                        st.info(
                            "*(O seleccioná otra fecha arriba si preferís no borrarlo)*"
                        )

                st.markdown("---")

                # PASO 2: CARGA Y PROCESAMIENTO DEL ARCHIVO CSV
                st.subheader("2️⃣ Paso 2: Subí el Reporte CSV de Recetas")
                archivo_subido = st.file_uploader(
                    "Seleccioná el archivo CSV de recetas", type=["csv"]
                )

                if archivo_subido is not None:
                    if (
                        "archivo_actual" not in st.session_state
                        or st.session_state.get("archivo_actual") != archivo_subido.name
                    ):
                        st.session_state["archivo_actual"] = archivo_subido.name
                        st.session_state.pop("df_lote_activo", None)
                        keys_to_del = [
                            k
                            for k in st.session_state.keys()
                            if k.startswith("fisico_")
                        ]
                        for k in keys_to_del:
                            st.session_state.pop(k, None)

                    try:
                        if "df_lote_activo" not in st.session_state:
                            contenido_bytes = archivo_subido.getvalue()
                            texto_decodificado = contenido_bytes.decode("latin1")
                            lineas = texto_decodificado.splitlines()

                            filas_datos = []
                            obra_social_actual = "GENERAL"

                            for i, linea in enumerate(lineas):
                                cols = [c.strip() for c in linea.split(";")]

                                # Detectar encabezado de Obra Social (Ej: A3390, A0406, A3718, A3378, etc.)
                                if (
                                    len(cols) > 1
                                    and cols[1].startswith("A")
                                    and cols[1][1:].isdigit()
                                ):
                                    # Buscar hacia arriba el nombre real de la Obra Social
                                    for offset in range(1, 6):
                                        if i - offset >= 0:
                                            linea_prev = lineas[i - offset].split(";")
                                            posibles_titulos = [
                                                c.strip("; ")
                                                for c in linea_prev
                                                if c.strip("; ")
                                            ]

                                            # Filtrar palabras clave del sistema y códigos 'A'
                                            cand = [
                                                t
                                                for t in posibles_titulos
                                                if not t.startswith("A")
                                                and "Mandataria" not in t
                                                and t.upper() != "PLAN"
                                            ]
                                            if cand:
                                                obra_social_actual = cand[0]
                                                break

                                # Extraer datos de la receta
                                for idx_c, val_c in enumerate(cols):
                                    if (
                                        len(val_c) == 13
                                        and val_c[:4].isdigit()
                                        and "-" in val_c
                                    ):
                                        plan_val = (
                                            cols[0]
                                            if cols[0] != ""
                                            and cols[0].upper() != "PLAN"
                                            else "PLAN GENERAL"
                                        )
                                        nro_ticket = val_c
                                        tt_val = ""
                                        for siguiente in cols[idx_c + 1 :]:
                                            if (
                                                len(siguiente) >= 10
                                                and "-" in siguiente
                                            ):
                                                tt_val = siguiente
                                                break
                                        if not tt_val:
                                            tt_val = "N/D"

                                        filas_datos.append(
                                            {
                                                "Obra Social": obra_social_actual,
                                                "Plan": plan_val,
                                                "Nro Ticket": nro_ticket,
                                                "T.T": tt_val,
                                                "Es Vale": False,
                                            }
                                        )
                                        break

                            if filas_datos:
                                df_base = pd.DataFrame(filas_datos)
                                df_base.insert(
                                    0,
                                    "ID_Fila",
                                    [f"REC_{i}" for i in range(len(df_base))],
                                )
                                st.session_state["df_lote_activo"] = df_base
                            else:
                                st.warning(
                                    "No se pudieron extraer recetas automáticamente con este formato."
                                )
                                st.stop()

                        df_activo = st.session_state["df_lote_activo"]

                        st.success(
                            f"¡Reporte cargado correctamente para el día {fecha_str_fmt}! Total de recetas detectadas: {len(df_activo)}"
                        )
                        st.markdown("---")

                        def actualizar_vales():
                            if (
                                "editor_vales" in st.session_state
                                and "edited_rows" in st.session_state["editor_vales"]
                            ):
                                cambios = st.session_state["editor_vales"][
                                    "edited_rows"
                                ]
                                for idx_fila_vis, datos_edit in cambios.items():
                                    if "Es Vale" in datos_edit:
                                        if (
                                            "df_filtrado_temp" in st.session_state
                                            and idx_fila_vis
                                            < len(st.session_state["df_filtrado_temp"])
                                        ):
                                            id_real = st.session_state[
                                                "df_filtrado_temp"
                                            ].iloc[idx_fila_vis]["ID_Fila"]
                                            nuevo_estado = datos_edit["Es Vale"]
                                            st.session_state["df_lote_activo"].loc[
                                                st.session_state["df_lote_activo"][
                                                    "ID_Fila"
                                                ]
                                                == id_real,
                                                "Es Vale",
                                            ] = nuevo_estado

                                            os_afectada = (
                                                st.session_state["df_lote_activo"]
                                                .loc[
                                                    st.session_state["df_lote_activo"][
                                                        "ID_Fila"
                                                    ]
                                                    == id_real,
                                                    "Obra Social",
                                                ]
                                                .values[0]
                                            )
                                            df_os_temp = st.session_state[
                                                "df_lote_activo"
                                            ][
                                                st.session_state["df_lote_activo"][
                                                    "Obra Social"
                                                ]
                                                == os_afectada
                                            ]
                                            nuevo_a_enviar = len(df_os_temp) - len(
                                                df_os_temp[
                                                    df_os_temp["Es Vale"] == True
                                                ]
                                            )
                                            st.session_state[
                                                f"fisico_{os_afectada}"
                                            ] = nuevo_a_enviar

                        st.subheader("📊 Control por Obra Social")

                        obras_sociales = df_activo["Obra Social"].unique()

                        for os_nombre in obras_sociales:
                            df_os = df_activo[df_activo["Obra Social"] == os_nombre]
                            total_csv = len(df_os)
                            vales_marcados = len(df_os[df_os["Es Vale"] == True])
                            a_enviar = total_csv - vales_marcados

                            key_fisico = f"fisico_{os_nombre}"
                            if key_fisico not in st.session_state:
                                st.session_state[key_fisico] = a_enviar

                            with st.container():
                                (
                                    c_os,
                                    c_tot,
                                    c_val,
                                    c_env,
                                    c_fis_label,
                                    c_fis_input,
                                    c_est,
                                ) = st.columns([2.2, 0.9, 0.9, 1, 1.2, 1.2, 0.6])

                                c_os.markdown(f"**{os_nombre}**")
                                c_tot.markdown(f"Total: **{total_csv}**")
                                c_val.markdown(f"Vales: **{vales_marcados}**")
                                c_env.markdown(f"A enviar: **{a_enviar}**")

                                c_fis_label.markdown("Enviadas físicamente:")

                                conteo_fisico = c_fis_input.number_input(
                                    "Físico",
                                    min_value=0,
                                    max_value=total_csv,
                                    key=key_fisico,
                                    label_visibility="collapsed",
                                )

                                if conteo_fisico != a_enviar:
                                    c_est.warning("⚠️")
                                else:
                                    c_est.success("✅")

                                st.markdown("---")

                        st.subheader("🔍 Detalle de Recetas y Marcado de Vales")

                        busqueda = st.text_input(
                            "🔎 Buscar por Nro de Ticket o T.T.",
                            placeholder="Ej: 0990-00043135 o 9909-00558021",
                        )

                        df_filtrado = df_activo.copy()
                        if busqueda:
                            df_filtrado = df_filtrado[
                                df_filtrado["Nro Ticket"].str.contains(
                                    busqueda, case=False, na=False
                                )
                                | df_filtrado["T.T"].str.contains(
                                    busqueda, case=False, na=False
                                )
                            ]

                        st.session_state["df_filtrado_temp"] = df_filtrado

                        st.info(
                            f"Mostrando {len(df_filtrado)} de {len(df_activo)} registros."
                        )

                        st.data_editor(
                            df_filtrado[
                                [
                                    "ID_Fila",
                                    "Obra Social",
                                    "Plan",
                                    "Nro Ticket",
                                    "T.T",
                                    "Es Vale",
                                ]
                            ],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "ID_Fila": None,
                                "Es Vale": st.column_config.CheckboxColumn(
                                    "Retener como Vale 🎫",
                                    help="Tildá esta casilla si la receta queda retenida en la sucursal por falta de medicación.",
                                    default=False,
                                ),
                            },
                            key="editor_vales",
                            on_change=actualizar_vales,
                        )

                        st.markdown("---")

                        referencia_usuario = st.text_input(
                            "📝 Nota / Referencia Opcional para el Lote (ej: Lote Tarde - Turno 2)"
                        )

                        id_lote_final = (
                            f"LOTE-{sucursal_actual}-{fecha_recetas.strftime('%Y%m%d')}"
                        )
                        btn_label = "🔒 Cerrar y Generar Lote para Mutuales"

                        if st.button(btn_label, type="primary"):
                            try:
                                total_vales_lote = len(
                                    df_activo[df_activo["Es Vale"] == True]
                                )
                                total_envio_lote = len(df_activo) - total_vales_lote

                                filas_os_pdf = []
                                for os_n in df_activo["Obra Social"].unique():
                                    df_sub = df_activo[df_activo["Obra Social"] == os_n]
                                    v_m = len(df_sub[df_sub["Es Vale"] == True])
                                    filas_os_pdf.append(
                                        {
                                            "Obra Social": os_n,
                                            "Total": len(df_sub),
                                            "Vales": v_m,
                                            "A Enviar": len(df_sub) - v_m,
                                        }
                                    )
                                df_resumen_os_pdf = pd.DataFrame(filas_os_pdf)
                                df_vales_pdf = df_activo[df_activo["Es Vale"] == True][
                                    ["Obra Social", "Plan", "Nro Ticket", "T.T"]
                                ]

                                obs_final = f"Enviadas: {total_envio_lote} | Vales: {total_vales_lote}"
                                if referencia_usuario:
                                    obs_final += f" | Ref: {referencia_usuario}"

                                data_lote = {
                                    "id_lote": id_lote_final,
                                    "sucursal": sucursal_actual,
                                    "fecha_carga": fecha_str_db,
                                    "estado": "Cerrado",
                                    "observacion": obs_final,
                                }

                                res_insert = (
                                    supabase.table("lotes").upsert(data_lote).execute()
                                )

                                if res_insert:
                                    st.session_state["lote_generado_exito"] = {
                                        "nombre": id_lote_final,
                                        "fecha": fecha_str_fmt,
                                        "referencia": (
                                            referencia_usuario
                                            if referencia_usuario
                                            else "Sin referencia"
                                        ),
                                        "total_envio": total_envio_lote,
                                        "total_vales": total_vales_lote,
                                        "resumen_os": df_resumen_os_pdf,
                                        "df_vales": df_vales_pdf,
                                    }
                                    st.rerun()
                                else:
                                    st.error(
                                        "No se pudo confirmar el guardado en la base de datos."
                                    )

                            except Exception as e:
                                st.error(f"Error al guardar el lote en Supabase: {e}")

                    except Exception as e:
                        st.error(f"Error al procesar el archivo CSV: {e}")

        # Pestaña de Historial con opción de Reimprimir PDF (Panel de Sucursal)
        with tab_historial:
            st.subheader("📜 Lotes Registrados y Reimpresión de Comprobantes")
            try:
                res_suc = (
                    supabase.table("lotes")
                    .select("*")
                    .order("fecha_carga", desc=True)
                    .execute()
                )

                if res_suc.data and len(res_suc.data) > 0:
                    for lote_h in res_suc.data:
                        with st.expander(
                            f"📦 Sucursal: {lote_h.get('sucursal')} — Fecha: {lote_h.get('fecha_carga')} — Ref: {lote_h.get('observacion')}"
                        ):
                            col_info, col_btn = st.columns([3, 1])
                            with col_info:
                                st.write(
                                    f"**Identificador:** `{lote_h.get('id_lote')}`"
                                )
                                st.write(f"**Sucursal:** {lote_h.get('sucursal')}")
                                st.write(
                                    f"**Fecha de carga / recetas:** {lote_h.get('fecha_carga')}"
                                )
                                st.write(
                                    f"**Observaciones:** {lote_h.get('observacion')}"
                                )
                            with col_btn:
                                st.write("")
                                if st.button(
                                    "📥 Reimprimir PDF",
                                    key=f"reimp_suc_{lote_h.get('id_lote')}",
                                ):
                                    pdf_reimp_bytes = generar_pdf_bytes(
                                        str(lote_h.get("sucursal")),
                                        str(lote_h.get("fecha_carga")),
                                        str(lote_h.get("observacion")),
                                        0,
                                        0,
                                        pd.DataFrame(),
                                        pd.DataFrame(),
                                    )
                                    st.download_button(
                                        label="💾 Descargar Archivo PDF",
                                        data=pdf_reimp_bytes,
                                        file_name=f"Historial_Lote_{lote_h.get('fecha_carga')}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_suc_{lote_h.get('id_lote')}",
                                    )
                else:
                    st.info(
                        "Aún no se registraron cierres de lote en la base de datos."
                    )
            except Exception as e:
                st.error(f"Error al recuperar el historial: {e}")

    elif rol == "mutual":
        st.header("🏥 Panel de Mutual / Obra Social")
        st.write("Bienvenido al módulo de auditoría de recetas y lotes enviados.")

    else:
        st.warning(
            "El usuario actual no tiene un rol válido asignado en la base de datos."
        )
