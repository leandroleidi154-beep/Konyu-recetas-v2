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
    sucursal_nombre,
    fecha_lote,
    observacion,
    total_envio,
    total_vales,
    df_resumen_os,
    df_vales,
):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)

    # Encabezado
    pdf.cell(190, 8, f"Resumen de Lote - Sucursal: {sucursal_nombre}", 0, 1, "C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(
        190, 6, f"Fecha del Lote: {fecha_lote} | Observación: {observacion}", 0, 1, "C"
    )
    pdf.ln(5)

    # Tabla 1: Resumen por Obra Social
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "1. Resumen por Obra Social (Recetas Enviadas)", 0, 1, "L")

    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(95, 7, "Obra Social", 1, 0, "C", True)
    pdf.cell(30, 7, "Total CSV", 1, 0, "C", True)
    pdf.cell(35, 7, "Vales Retenidos", 1, 0, "C", True)
    pdf.cell(30, 7, "Físico Enviado", 1, 1, "C", True)

    pdf.set_font("Arial", "", 9)
    total_csv_acum = 0
    total_vales_acum = 0
    total_fisico_acum = 0

    if not df_resumen_os.empty:
        for _, row_os in df_resumen_os.iterrows():
            val_total = row_os.get("Total CSV", row_os.get("Total", 0))
            val_vales = row_os.get("Vales Retenidos", row_os.get("Vales", 0))
            val_fisico = row_os.get(
                "Físico Enviado", row_os.get("A Enviar", val_total - val_vales)
            )

            total_csv_acum += int(val_total)
            total_vales_acum += int(val_vales)
            total_fisico_acum += int(val_fisico)

            pdf.cell(95, 6, str(row_os.get("Obra Social", "")), 1, 0, "L")
            pdf.cell(30, 6, str(val_total), 1, 0, "C")
            pdf.cell(35, 6, str(val_vales), 1, 0, "C")
            pdf.cell(30, 6, str(val_fisico), 1, 1, "C")

    pdf.ln(5)

    # Tabla 2: Detalle de Vales Retenidos en Sucursal
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "2. Detalle de Vales Retenidos en Sucursal", 0, 1, "L")

    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(50, 7, "Obra Social", 1, 0, "C", True)
    pdf.cell(45, 7, "Plan", 1, 0, "C", True)
    pdf.cell(50, 7, "Nro Ticket", 1, 0, "C", True)
    pdf.cell(45, 7, "T.T", 1, 1, "C", True)

    pdf.set_font("Arial", "", 8)
    if not df_vales.empty:
        for _, row_v in df_vales.iterrows():
            pdf.cell(50, 6, str(row_v.get("Obra Social", "")), 1, 0, "L")
            pdf.cell(45, 6, str(row_v.get("Plan", "")), 1, 0, "L")
            pdf.cell(50, 6, str(row_v.get("Nro Ticket", "")), 1, 0, "C")
            pdf.cell(45, 6, str(row_v.get("T.T", "")), 1, 1, "C")
    else:
        pdf.cell(190, 6, "No se retuvieron vales en este lote.", 1, 1, "C")

    pdf.ln(8)

    # Cuadro de Totales Generales Resaltado y Ajustado
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 9)

    envio_final = total_envio if total_envio > 0 else total_fisico_acum
    vales_final = total_vales if total_vales > 0 else total_vales_acum
    procesadas_final = (
        total_csv_acum if total_csv_acum > 0 else (envio_final + vales_final)
    )

    texto_totales = (
        f"TOTAL GENERAL:  "
        f"Procesadas (CSV): {procesadas_final}  |  "
        f"Vales Retenidos: {vales_final}  |  "
        f"A Enviar: {procesadas_final - vales_final}  |  "
        f"Físicas Enviadas: {envio_final}"
    )

    pdf.cell(190, 10, texto_totales, 1, 1, "C", True)

    return pdf.output(dest="S").encode("latin1")


# --- PANTALLA DE LOGIN ---
if st.session_state["usuario_logueado"] is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image(
                "assets/konyu_login.png", width=180
            )  # <-- Aumentamos el tamaño a 180
        except Exception:
            pass
        st.title("Konyu Recetas - Sistema de Gestión de Recetas")
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
    with st.sidebar:
        # Foto de Konyu grande + Título en el menú lateral
        col_side_img, col_side_txt = st.columns([1, 2.5])
        with col_side_img:
            try:
                st.image("assets/konyu_sidebar.png", width=95)
            except Exception:
                pass
        with col_side_txt:
            st.markdown(
                "<h3 style='margin: 0; padding-top: 5px;'>Konyu Recetas</h3>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # Datos de usuario y rol con texto más grande y prolijo
        nom_usr = user.get("nombre", "Desconocido")
        rol_usr = str(user.get("rol", "Sin Rol")).capitalize()

        st.markdown(
            f"""
            <div style="font-size: 17px; line-height: 1.8; margin-bottom: 15px;">
                <b>👤 Usuario:</b> <span style="color: #ff4b4b; font-weight: bold;">{nom_usr}</span><br>
                <b>🔑 Rol:</b> <span>{rol_usr}</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.markdown("---")

    rol = str(user.get("rol", "")).lower()

    # Vistas según el rol asignado
    if rol == "administrador":
        col_head_left, col_head_right = st.columns([3, 1])

        with col_head_left:
            st.header("👑 Panel de Administrador - Gestión de Usuarios")

        with col_head_right:
            try:
                st.image("assets/konyu_header.png", width=90)
                st.markdown(
                    "<p style='color: rgba(250, 250, 250, 0.55); font-style: italic; font-size: 13px; margin-top: -5px;'>“Konyu supervisando el sistema...”</p>",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass

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
        col_head_left, col_head_right = st.columns([3, 1])

        with col_head_left:
            st.header("🏪 Panel de Sucursal - Control y Generación de Lotes")

        with col_head_right:
            try:
                st.image("assets/konyu_header.png", width=90)
                st.markdown(
                    "<p style='color: rgba(250, 250, 250, 0.55); font-style: italic; font-size: 13px; margin-top: -5px;'>“Konyu supervisando el stock...”</p>",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass

        # Definimos la sucursal fija para toda la vista y evitar errores en las solapas
        sucursal_actual = user.get("nombre", "Sucursal")

        tab_cierre, tab_historial, tab_vales = st.tabs(
            ["🔒 Cierre de Lote", "📜 Historial de Lotes", "📋 Registro de Vales"]
        )

        with tab_cierre:
            # Si ya se generó un lote con éxito
            if "lote_generado_exito" in st.session_state:
                lote_info = st.session_state["lote_generado_exito"]
                st.success(
                    f"¡Lote del día **{lote_info['fecha']}** guardado y cerrado con éxito!"
                )
                st.markdown("---")
                col_resumen_txt, col_konyu_lote = st.columns([2, 1])

                with col_resumen_txt:
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

                with col_konyu_lote:
                    try:
                        st.image("assets/konyu_lote.png", width=110)
                        st.markdown(
                            "<p style='color: rgba(250, 250, 250, 0.6); font-style: italic; font-size: 12px;'>“¡Lote listo para enviar a Mutuales!” 🐾</p>",
                            unsafe_allow_html=True,
                        )
                    except Exception:
                        pass
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

                                if (
                                    len(cols) > 1
                                    and cols[1].startswith("A")
                                    and cols[1][1:].isdigit()
                                ):
                                    if i - 1 >= 0:
                                        linea_prev = lineas[i - 1].split(";")
                                        posibles_titulos = [
                                            c.strip("; \n")
                                            for c in linea_prev
                                            if c.strip("; \n")
                                        ]

                                        cand = [
                                            t.strip()
                                            for t in posibles_titulos
                                            if t.strip()
                                            and not (
                                                t.startswith("A")
                                                and len(t) < 6
                                                and t[1:].isdigit()
                                            )
                                            and not t.isdigit()
                                            and "Mandataria" not in t
                                            and "$" not in t
                                            and "Tk" not in t
                                            and "Os" not in t
                                            and t.upper()
                                            not in ["COMP", "REC", "NC/A", "PLAN"]
                                        ]
                                        if cand:
                                            obra_social_actual = cand[0]

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

                        st.subheader("📊 Control por Obra Social y Conteo Físico")
                        st.caption(
                            "Podés tildar 'Seleccionar todo' en la fila de la Obra Social o desplegar para tildar receta por receta con el teclado (Espacio/Enter)."
                        )

                        obras_sociales = df_activo["Obra Social"].unique()

                        if "recetas_verificadas" not in st.session_state:
                            st.session_state["recetas_verificadas"] = set()

                        # --- FUNCIÓN CALLBACK PARA EL BOTÓN MAESTRO ---
                        def toggle_todos_os(os_nombre_cb, ids_os_cb):
                            key_chk = f"chk_main_{os_nombre_cb}"
                            if st.session_state.get(key_chk, False):
                                st.session_state["recetas_verificadas"].update(ids_os_cb)
                            else:
                                st.session_state["recetas_verificadas"].difference_update(ids_os_cb)

                        for os_nombre in obras_sociales:
                            df_os_todas = df_activo[
                                df_activo["Obra Social"] == os_nombre
                            ].copy()
                            total_csv = len(df_os_todas)

                            # Recetas que NO son vales (las que realmente deben ir físicamente)
                            df_os_fisicas = df_os_todas[
                                df_os_todas["Es Vale"] == False
                            ].copy()
                            vales_os = total_csv - len(df_os_fisicas)
                            total_a_enviar_os = len(df_os_fisicas)

                            ids_fisicas_os = set(df_os_fisicas["ID_Fila"])

                            # Verificadas reales sobre las que NO son vales
                            verificadas_os = len(
                                ids_fisicas_os.intersection(
                                    st.session_state["recetas_verificadas"]
                                )
                            )

                            key_fisico = f"fisico_{os_nombre}"
                            st.session_state[key_fisico] = verificadas_os

                            with st.container():
                                (
                                    c_chk_fast,
                                    c_os,
                                    c_tot,
                                    c_val,
                                    c_env,
                                    c_fis_label,
                                    c_fis_val,
                                    c_est,
                                ) = st.columns([0.4, 2.0, 0.8, 0.8, 0.8, 1.2, 0.7, 0.5])

                                # Tilde rápido en la fila principal
                                todaseleccionadas = (
                                    verificadas_os == total_a_enviar_os
                                    and total_a_enviar_os > 0
                                )
                                chk_rapido = c_chk_fast.checkbox(
                                    "",
                                    value=todaseleccionadas,
                                    key=f"chk_main_{os_nombre}",
                                    help="Tildá acá para marcar TODAS las físicas de esta Obra Social automáticamente.",
                                    on_change=toggle_todos_os,
                                    args=(os_nombre, ids_fisicas_os)
                                )


                                c_os.markdown(f"**{os_nombre}**")
                                c_tot.markdown(f"Total: **{total_csv}**")
                                c_val.markdown(f"Vales: **{vales_os}**")
                                c_env.markdown(f"A enviar: **{total_a_enviar_os}**")

                                c_fis_label.markdown("Enviadas físicamente:")
                                c_fis_val.markdown(
                                    f"**{verificadas_os} / {total_a_enviar_os}**"
                                )

                                if (
                                    verificadas_os == total_a_enviar_os
                                    and total_a_enviar_os >= 0
                                ):
                                    c_est.success("✅")
                                else:
                                    c_est.warning("⏳")

                                # --- DESPLEGABLE CON SOLO RECETAS A ENVIAR (EXCLUYE VALES) ---
                                with st.expander(
                                    f"🔍 Auditables: {total_a_enviar_os} receta(s) física(s) de {os_nombre}"
                                ):
                                    if total_a_enviar_os > 0:
                                        st.caption(
                                            "💡 *Tip: Navegá con flechas ↓ y tildá rápido con 'Espacio' o 'Enter'.*"
                                        )

                                        df_os_editor = df_os_fisicas.copy()
                                        df_os_editor["Físico OK"] = df_os_editor[
                                            "ID_Fila"
                                        ].isin(st.session_state["recetas_verificadas"])

                                        edited_df_os = st.data_editor(
                                            df_os_editor[
                                                [
                                                    "ID_Fila",
                                                    "Plan",
                                                    "Nro Ticket",
                                                    "T.T",
                                                    "Físico OK",
                                                ]
                                            ],
                                            use_container_width=True,
                                            hide_index=True,
                                            column_config={
                                                "ID_Fila": None,
                                                "Físico OK": st.column_config.CheckboxColumn(
                                                    "Receta Presente 📄",
                                                    help="Tildá si tenés el papel físico.",
                                                    default=False,
                                                ),
                                            },
                                            key=f"editor_fisico_os_{os_nombre}",
                                        )

                                        # Sincronización
                                        cambios_detectados = False
                                        for _, row_e in edited_df_os.iterrows():
                                            id_f = row_e["ID_Fila"]
                                            verif = row_e["Físico OK"]

                                            if (
                                                verif
                                                and id_f
                                                not in st.session_state[
                                                    "recetas_verificadas"
                                                ]
                                            ):
                                                st.session_state[
                                                    "recetas_verificadas"
                                                ].add(id_f)
                                                cambios_detectados = True
                                            elif (
                                                not verif
                                                and id_f
                                                in st.session_state[
                                                    "recetas_verificadas"
                                                ]
                                            ):
                                                st.session_state[
                                                    "recetas_verificadas"
                                                ].discard(id_f)
                                                cambios_detectados = True

                                        if cambios_detectados:
                                            st.rerun()
                                    else:
                                        st.info(
                                            "Todas las recetas de esta Obra Social están marcadas como Vale o no hay ítems."
                                        )

                                st.markdown("---")

                        # --- TABLA APARTE PARA MARCADO DE VALES ---
                        st.subheader("🔍 Detalle General y Marcado de Vales (Aparte)")
                        st.caption(
                            "Utilizá esta sección exclusivamente si necesitás retener recetas como vales por falta de medicación."
                        )

                        busqueda = st.text_input(
                            "🔎 Buscar por Nro de Ticket o T.T.",
                            placeholder="Ej: 0990-00043135 o 9909-00558021",
                            key="busqueda_vales_general",  # <--- CLAVE ÚNICA AGREGADA AQUÍ
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
                                            # Si pasa a ser Vale, le quitamos el tilde físico si lo tenía
                                            if (
                                                nuevo_estado
                                                and id_real
                                                in st.session_state.get(
                                                    "recetas_verificadas", set()
                                                )
                                            ):
                                                st.session_state[
                                                    "recetas_verificadas"
                                                ].discard(id_real)

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
                                    help="Tildá esta casilla si la receta queda retenida en la sucursal.",
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

                        # --- CÁLCULO PREVIO PARA VALIDACIÓN DE AUDITORÍA ---
                        total_vales_lote_check = len(
                            df_activo[df_activo["Es Vale"] == True]
                        )
                        
                        total_auditables_check = 0
                        for os_n in df_activo["Obra Social"].unique():
                            df_sub = df_activo[df_activo["Obra Social"] == os_n]
                            v_m = len(df_sub[df_sub["Es Vale"] == True])
                            total_auditables_check += (len(df_sub) - v_m)

                        recetas_marcadas_actuales = len(st.session_state.get("recetas_verificadas", set()))
                        faltan_verificar = total_auditables_check - recetas_marcadas_actuales

                        if faltan_verificar > 0:
                            st.warning(
                                f"⚠️ **Atención:** Todavía te faltan **{faltan_verificar}** receta(s) física(s) por tildar o auditar. "
                                f"Revisá los desplegables de las Obras Sociales para completar el 100% antes de cerrar el lote."
                            )

                        # El botón estará deshabilitado visualmente si faltan recetas por tildar
                        if st.button(btn_label, type="primary", disabled=(faltan_verificar > 0)):
                            try:
                                total_vales_lote = total_vales_lote_check
                                filas_os_pdf = []
                                total_envio_lote = 0

                                for os_n in df_activo["Obra Social"].unique():
                                    df_sub = df_activo[df_activo["Obra Social"] == os_n]
                                    total_csv_os = len(df_sub)
                                    v_m = len(df_sub[df_sub["Es Vale"] == True])

                                    key_fisico = f"fisico_{os_n}"
                                    fisico_ingresado = st.session_state.get(
                                        key_fisico, total_csv_os - v_m
                                    )

                                    total_envio_lote += fisico_ingresado

                                    filas_os_pdf.append(
                                        {
                                            "Obra Social": os_n,
                                            "Total CSV": total_csv_os,
                                            "Vales Retenidos": v_m,
                                            "Físico Enviado": fisico_ingresado,
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
                                    df_vales_a_guardar = df_activo[
                                        df_activo["Es Vale"] == True
                                    ]
                                    supabase.table("vales").delete().eq(
                                        "id_lote", id_lote_final
                                    ).execute()

                                    if not df_vales_a_guardar.empty:
                                        vales_records = []
                                        for idx, row_v in df_vales_a_guardar.iterrows():
                                            vales_records.append(
                                                {
                                                    "id_vale": f"{id_lote_final}_VALE_{idx}",
                                                    "id_lote": id_lote_final,
                                                    "sucursal": sucursal_actual,
                                                    "fecha_origen": fecha_str_db,
                                                    "obra_social": row_v.get(
                                                        "Obra Social"
                                                    ),
                                                    "plan": row_v.get("Plan"),
                                                    "n_ticket": row_v.get("Nro Ticket"),
                                                    "tt_tramitacion": row_v.get("T.T"),
                                                    "estado": "Pendiente",
                                                }
                                            )
                                        supabase.table("vales").insert(
                                            vales_records
                                        ).execute()

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
                    .eq("sucursal", sucursal_actual)
                    .order("fecha_carga", desc=True)
                    .execute()
                )

                if res_suc.data and len(res_suc.data) > 0:
                    for lote_h in res_suc.data:
                        estado_actual_lote = lote_h.get("estado", "Cerrado")
                        with st.expander(
                            f"📦 Fecha: {lote_h.get('fecha_carga')} — Estado: [{estado_actual_lote}] — Ref: {lote_h.get('observacion')}"
                        ):
                            col_info, col_btn = st.columns([3, 1])
                            with col_info:
                                st.write(
                                    f"**Identificador:** `{lote_h.get('id_lote')}`"
                                )
                                st.write(f"**Sucursal:** {lote_h.get('sucursal')}")
                                st.write(f"**Estado actual:** {estado_actual_lote}")

                                if estado_actual_lote == "Recibido por Mutual":
                                    st.success(
                                        "✅ La Mutual ya confirmó la recepción física de este lote."
                                    )
                                else:
                                    st.info(
                                        "⏳ Aguardando recepción por parte de la Mutual."
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

        # 📋 Pestaña de Registro y Gestión de Vales (Con acciones inteligentes por estado)
        with tab_vales:
            st.subheader("📋 Registro y Seguimiento de Vales Retenidos")

            if "vales_seleccionados_ids" not in st.session_state:
                st.session_state["vales_seleccionados_ids"] = []

            # 1. Filtros de Búsqueda
            col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.5, 2, 1])

            with col_f1:
                filtro_estado = st.selectbox(
                    "Estado",
                    [
                        "Todos",
                        "Pendiente",
                        "Enviado",
                        "Recibido por Mutual",
                        "Cancelado",
                    ],
                    key="filtro_estado_vales_sucursal",
                )
            with col_f2:
                usar_todas_fechas = st.checkbox(
                    "Ver todas las fechas", value=True, key="vales_chk_fechas"
                )
            with col_f3:
                fecha_filtro_vales = st.date_input(
                    "Fecha de Origen",
                    disabled=usar_todas_fechas,
                    key="vales_fecha_origen",
                )
            with col_f4:
                busqueda_vales = st.text_input(
                    "🔍 Ticket o T.T.",
                    placeholder="Ej: 12345",
                    key="vales_busqueda_txt",
                )

            try:
                # 2. Consulta a Supabase
                query_v = (
                    supabase.table("vales").select("*").eq("sucursal", sucursal_actual)
                )

                if filtro_estado != "Todos":
                    query_v = query_v.eq("estado", filtro_estado)

                if not usar_todas_fechas:
                    query_v = query_v.eq("fecha_origen", str(fecha_filtro_vales))

                res_vales_db = query_v.execute()
                data_v = res_vales_db.data

                if data_v:
                    df_v_db = pd.DataFrame(data_v)

                    # Buscador por texto
                    if busqueda_vales:
                        df_v_db = df_v_db[
                            df_v_db["n_ticket"]
                            .astype(str)
                            .str.contains(busqueda_vales, case=False, na=False)
                            | df_v_db["tt_tramitacion"]
                            .astype(str)
                            .str.contains(busqueda_vales, case=False, na=False)
                        ]

                    if not df_v_db.empty:
                        st.info(
                            f"Mostrando {len(df_v_db)} vales en pantalla. Tildá para sumar a la lista."
                        )

                        # Marcar seleccionados guardados en sesión
                        df_v_db["Seleccionar"] = df_v_db["id_vale"].isin(
                            st.session_state["vales_seleccionados_ids"]
                        )

                        # Tabla interactiva
                        df_editado_vales = st.data_editor(
                            df_v_db[
                                [
                                    "Seleccionar",
                                    "fecha_origen",
                                    "obra_social",
                                    "plan",
                                    "n_ticket",
                                    "tt_tramitacion",
                                    "estado",
                                    "id_vale",
                                ]
                            ],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Seleccionar": st.column_config.CheckboxColumn(
                                    "☑️", default=False
                                ),
                                "fecha_origen": "Fecha",
                                "obra_social": "Obra Social",
                                "plan": "Plan",
                                "n_ticket": "Nº Ticket",
                                "tt_tramitacion": "T.T.",
                                "estado": "Estado",
                                "id_vale": None,
                            },
                            key="editor_acumulativo_vales",
                        )

                        # Sincronizar selección con el session_state
                        for _, row in df_editado_vales.iterrows():
                            vid = row["id_vale"]
                            seleccionado = row["Seleccionar"]
                            if (
                                seleccionado
                                and vid
                                not in st.session_state["vales_seleccionados_ids"]
                            ):
                                st.session_state["vales_seleccionados_ids"].append(vid)
                            elif (
                                not seleccionado
                                and vid in st.session_state["vales_seleccionados_ids"]
                            ):
                                st.session_state["vales_seleccionados_ids"].remove(vid)

                        st.markdown("---")
                        st.subheader("🛒 Vales Acumulados para Procesar")

                        ids_acumulados = st.session_state["vales_seleccionados_ids"]

                        if ids_acumulados:
                            res_acum = (
                                supabase.table("vales")
                                .select("*")
                                .in_("id_vale", ids_acumulados)
                                .execute()
                            )
                            if res_acum.data:
                                df_acumulado = pd.DataFrame(res_acum.data)

                                st.dataframe(
                                    df_acumulado[
                                        [
                                            "fecha_origen",
                                            "obra_social",
                                            "plan",
                                            "n_ticket",
                                            "tt_tramitacion",
                                            "estado",
                                        ]
                                    ],
                                    use_container_width=True,
                                    hide_index=True,
                                )

                                cant_total_sel = len(ids_acumulados)
                                estados_presentes = set(df_acumulado["estado"].tolist())

                                # Evaluación de estados
                                solo_pendientes = estados_presentes == {"Pendiente"}
                                solo_enviados = estados_presentes == {"Enviado"}
                                solo_cancelados = estados_presentes == {"Cancelado"}
                                solo_revertibles = solo_enviados or solo_cancelados
                                estados_mezclados = len(estados_presentes) > 1

                                if estados_mezclados:
                                    st.warning(
                                        "⚠️ Seleccionaste vales con diferentes estados. Te recomendamos procesar cada grupo por separado."
                                    )

                                col_acc1, col_acc2, col_acc3, col_acc4 = st.columns(
                                    [2, 1.5, 1.5, 1]
                                )

                                with col_acc1:
                                    if solo_pendientes:
                                        fecha_envio_masivo = st.date_input(
                                            "Fecha de Envío Real"
                                        )
                                        if st.button(
                                            f"🚀 Enviar ({cant_total_sel}) elegidos",
                                            type="primary",
                                        ):
                                            for id_v in ids_acumulados:
                                                supabase.table("vales").update(
                                                    {
                                                        "estado": "Enviado",
                                                        "fecha_resolucion": str(
                                                            fecha_envio_masivo
                                                        ),
                                                    }
                                                ).eq("id_vale", id_v).execute()
                                            st.session_state[
                                                "vales_seleccionados_ids"
                                            ] = []
                                            st.success(
                                                f"¡{cant_total_sel} vale(s) marcados como Enviados!"
                                            )
                                            st.rerun()

                                    elif solo_revertibles:
                                        st.write("")
                                        st.write("")
                                        if st.button(
                                            f"🔄 Revertir ({cant_total_sel}) a Pendiente",
                                            type="secondary",
                                        ):
                                            for id_v in ids_acumulados:
                                                supabase.table("vales").update(
                                                    {
                                                        "estado": "Pendiente",
                                                        "fecha_resolucion": None,
                                                    }
                                                ).eq("id_vale", id_v).execute()
                                            st.session_state[
                                                "vales_seleccionados_ids"
                                            ] = []
                                            st.info(
                                                f"¡{cant_total_sel} vale(s) devueltos al estado Pendiente!"
                                            )
                                            st.rerun()
                                    else:
                                        st.button(
                                            "🚀 Enviar elegidos",
                                            disabled=True,
                                            help="No podés enviar registros que ya están Enviados o Cancelados.",
                                        )

                                with col_acc2:
                                    st.write("")
                                    st.write("")
                                    if st.button(f"❌ Cancelar ({cant_total_sel})"):
                                        for id_v in ids_acumulados:
                                            supabase.table("vales").update(
                                                {"estado": "Cancelado"}
                                            ).eq("id_vale", id_v).execute()
                                        st.session_state["vales_seleccionados_ids"] = []
                                        st.warning(
                                            f"{cant_total_sel} vale(s) cancelados."
                                        )
                                        st.rerun()

                                with col_acc3:
                                    st.write("")
                                    st.write("")
                                    if st.button(f"🗑️ Eliminar ({cant_total_sel})"):
                                        for id_v in ids_acumulados:
                                            supabase.table("vales").delete().eq(
                                                "id_vale", id_v
                                            ).execute()
                                        st.session_state["vales_seleccionados_ids"] = []
                                        st.error(
                                            f"{cant_total_sel} vale(s) eliminados."
                                        )
                                        st.rerun()

                                with col_acc4:
                                    st.write("")
                                    st.write("")
                                    if st.button("🧹 Limpiar lista"):
                                        st.session_state["vales_seleccionados_ids"] = []
                                        st.rerun()
                        else:
                            st.caption(
                                "Aún no hay vales seleccionados. Tildá los elementos arriba para agregarlos a la lista acumulativa."
                            )

                    else:
                        st.info("No hay vales que coincidan con la búsqueda.")
                else:
                    st.info("No hay vales registrados con los filtros elegidos.")

            except Exception as e:
                st.error(f"Error al cargar los vales desde la base de datos: {e}")

    elif rol == "mutual":
        col_head_left, col_head_right = st.columns([3, 1])

        with col_head_left:
            st.header("🏥 Panel de Mutual / Obra Social")
            st.write("Bienvenido al módulo de auditoría de recetas y lotes enviados.")

        with col_head_right:
            try:
                st.image("assets/konyu_header.png", width=90)
                st.markdown(
                    "<p style='color: rgba(250, 250, 250, 0.55); font-style: italic; font-size: 13px; margin-top: -5px;'>“Konyu auditando auditorías...”</p>",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass

        # Obtenemos la lista de sucursales disponibles desde la base de datos de usuarios o lotes
        try:
            res_sucursales = (
                supabase.table("usuarios")
                .select("nombre")
                .eq("rol", "Sucursal")
                .execute()
            )
            lista_sucursales = (
                [s["nombre"] for s in res_sucursales.data]
                if res_sucursales.data
                else ["sucursal_1"]
            )
        except Exception:
            lista_sucursales = ["sucursal_1"]

        sucursal_seleccionada = st.selectbox(
            "🏢 Seleccione la Sucursal a Auditar:", lista_sucursales
        )

        # Pestañas principales para el sector de mutuales (Agregamos la pestaña de Vales Recibidos)
        tab_lotes_mutual, tab_vales_mutual, tab_vales_recibidos_mut = st.tabs(
            ["📦 Recepción de Lotes", "🎫 Seguimiento y Vales", "✅ Vales Recibidos"]
        )

        # --- PESTAÑA 1: RECEPCIÓN DE LOTES ---
        with tab_lotes_mutual:
            st.subheader(f"📦 Lotes de Recetas de la sucursal: {sucursal_seleccionada}")
            try:
                res_lotes_mut = (
                    supabase.table("lotes")
                    .select("*")
                    .eq("sucursal", sucursal_seleccionada)
                    .order("fecha_carga", desc=True)
                    .execute()
                )

                if res_lotes_mut.data:
                    for lote_m in res_lotes_mut.data:
                        estado_lote = lote_m.get("estado", "Cerrado")
                        with st.expander(
                            f"📁 Lote: {lote_m.get('id_lote')} — Fecha: {lote_m.get('fecha_carga')} — Estado: [{estado_lote}]"
                        ):
                            st.write(f"**Observación:** {lote_m.get('observacion')}")
                            st.write(
                                f"**Fecha de creación:** {lote_m.get('created_at')}"
                            )

                            col_m1, col_m2 = st.columns(2)

                            with col_m1:
                                if estado_lote != "Recibido por Mutual":
                                    if st.button(
                                        f"✅ Marcar Lote como RECIBIDO",
                                        key=f"ok_lote_{lote_m.get('id_lote')}",
                                    ):
                                        supabase.table("lotes").update(
                                            {"estado": "Recibido por Mutual"}
                                        ).eq("id_lote", lote_m.get("id_lote")).execute()
                                        st.success(
                                            "¡Lote marcado como recibido con éxito!"
                                        )
                                        st.rerun()
                                else:
                                    st.info(
                                        "👍 Este lote ya cuenta con el OK de recepción."
                                    )
                                    if st.button(
                                        f"🔄 Revertir Lote a 'Cerrado'",
                                        key=f"rev_lote_{lote_m.get('id_lote')}",
                                    ):
                                        supabase.table("lotes").update(
                                            {"estado": "Cerrado"}
                                        ).eq("id_lote", lote_m.get("id_lote")).execute()
                                        st.warning(
                                            "Se ha revertido el estado del lote."
                                        )
                                        st.rerun()

                            with col_m2:
                                st.write("📄 **Comprobante PDF**")
                                if st.button(
                                    f"📥 Descargar Resumen PDF",
                                    key=f"pdf_mut_{lote_m.get('id_lote')}",
                                ):
                                    pdf_bytes_mut = generar_pdf_bytes(
                                        str(lote_m.get("sucursal")),
                                        str(lote_m.get("fecha_carga")),
                                        str(lote_m.get("observacion")),
                                        0,
                                        0,
                                        pd.DataFrame(),
                                        pd.DataFrame(),
                                    )
                                    st.download_button(
                                        label="💾 Guardar PDF en equipo",
                                        data=pdf_bytes_mut,
                                        file_name=f"Comprobante_Lote_{lote_m.get('fecha_carga')}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_pdf_mut_{lote_m.get('id_lote')}",
                                    )
                else:
                    st.info(
                        f"No hay lotes registrados para la sucursal {sucursal_seleccionada}."
                    )
            except Exception as e:
                st.error(f"Error al cargar los lotes para la mutual: {e}")

        # --- PESTAÑA 2: SEGUIMIENTO Y VALES EN TRÁNSITO/PENDIENTES ---
        with tab_vales_mutual:
            st.subheader(
                f"🎫 Vales En Tránsito o Pendientes — Sucursal: {sucursal_seleccionada}"
            )

            try:
                # Mostramos por defecto los vales que están Enviados o Pendientes para que la mutual los gestione
                res_v_mut = (
                    supabase.table("vales")
                    .select("*")
                    .eq("sucursal", sucursal_seleccionada)
                    .in_("estado", ["Enviado", "Pendiente"])
                    .execute()
                )

                if res_v_mut.data:
                    df_v_mut = pd.DataFrame(res_v_mut.data)
                    df_v_mut["Seleccionar"] = False

                    st.info(
                        f"Se encontraron {len(df_v_mut)} vales pendientes o en tránsito."
                    )

                    df_edit_mut = st.data_editor(
                        df_v_mut[
                            [
                                "Seleccionar",
                                "fecha_origen",
                                "obra_social",
                                "plan",
                                "n_ticket",
                                "tt_tramitacion",
                                "estado",
                                "fecha_resolucion",
                                "id_vale",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Seleccionar": st.column_config.CheckboxColumn(
                                "☑️", default=False
                            ),
                            "fecha_origen": "Fecha Origen",
                            "obra_social": "Obra Social",
                            "plan": "Plan",
                            "n_ticket": "Nº Ticket",
                            "tt_tramitacion": "T.T.",
                            "estado": "Estado",
                            "fecha_resolucion": "Fecha Envío Sucursal",
                            "id_vale": None,
                        },
                        key="editor_vales_mutual_transito",
                    )

                    vales_sel_mut = df_edit_mut[df_edit_mut["Seleccionar"] == True]

                    if not vales_sel_mut.empty:
                        ids_mut_procesar = vales_sel_mut["id_vale"].tolist()
                        cant_mut = len(ids_mut_procesar)

                        st.markdown("---")
                        if st.button(
                            f"📥 Confirmar Recepción Física ({cant_mut}) Vales",
                            type="primary",
                        ):
                            for id_vm in ids_mut_procesar:
                                supabase.table("vales").update(
                                    {"estado": "Recibido por Mutual"}
                                ).eq("id_vale", id_vm).execute()
                            st.success(
                                f"¡Se confirmó la recepción física de {cant_mut} vale(s)!"
                            )
                            st.rerun()
                else:
                    st.info(
                        "No hay vales pendientes ni en tránsito para esta sucursal."
                    )

            except Exception as e:
                st.error(f"Error al consultar vales: {e}")

        # --- PESTAÑA 3: VALES RECIBIDOS (Con opción de revertir) ---
        with tab_vales_recibidos_mut:
            st.subheader(
                f"✅ Vales Ya Recibidos por la Mutual — Sucursal: {sucursal_seleccionada}"
            )

            try:
                res_recibidos = (
                    supabase.table("vales")
                    .select("*")
                    .eq("sucursal", sucursal_seleccionada)
                    .eq("estado", "Recibido por Mutual")
                    .execute()
                )

                if res_recibidos.data:
                    df_recibidos = pd.DataFrame(res_recibidos.data)
                    df_recibidos["Seleccionar"] = False

                    st.info(
                        f"Hay {len(df_recibidos)} vales con recepción confirmada por la mutual."
                    )

                    df_edit_recibidos = st.data_editor(
                        df_recibidos[
                            [
                                "Seleccionar",
                                "fecha_origen",
                                "obra_social",
                                "plan",
                                "n_ticket",
                                "tt_tramitacion",
                                "fecha_resolucion",
                                "id_vale",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Seleccionar": st.column_config.CheckboxColumn(
                                "☑️", default=False
                            ),
                            "fecha_origen": "Fecha Origen",
                            "obra_social": "Obra Social",
                            "plan": "Plan",
                            "n_ticket": "Nº Ticket",
                            "tt_tramitacion": "T.T.",
                            "fecha_resolucion": "Fecha Envío",
                            "id_vale": None,
                        },
                        key="editor_vales_mutual_recibidos",
                    )

                    vales_sel_rec = df_edit_recibidos[
                        df_edit_recibidos["Seleccionar"] == True
                    ]

                    if not vales_sel_rec.empty:
                        ids_rec_procesar = vales_sel_rec["id_vale"].tolist()
                        cant_rec = len(ids_rec_procesar)

                        st.markdown("---")
                        if st.button(
                            f"🔄 Revertir ({cant_rec}) Vales a estado 'Enviado'",
                            type="secondary",
                        ):
                            for id_vm in ids_rec_procesar:
                                supabase.table("vales").update(
                                    {"estado": "Enviado"}
                                ).eq("id_vale", id_vm).execute()
                            st.warning(
                                f"Se revirtieron {cant_rec} vale(s) al estado Enviado."
                            )
                            st.rerun()
                else:
                    st.info(
                        "No hay vales registrados como recibidos para esta sucursal todavía."
                    )

            except Exception as e:
                st.error(f"Error al consultar vales recibidos: {e}")
    else:
        st.warning(
            "El usuario actual no tiene un rol válido asignado en la base de datos."
        )
