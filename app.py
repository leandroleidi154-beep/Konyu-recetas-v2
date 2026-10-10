import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# 1. Configuración de la página
st.set_page_config(
    page_title="Gestión de Recetas - Konyu",
    page_icon="💊",
    layout="wide"
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
        self.cell(0, 6, f"Sucursal: {self.sucursal}  |  Fecha de Recetas: {self.fecha_str}", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 6, f"Referencia: {self.ref_lote}", 0, 1, "C")
        self.ln(4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

def generar_pdf_bytes(sucursal, fecha_str, ref_lote, total_envio, total_vales, df_os_resumen, df_vales_det):
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
    pdf.cell(190, 8, f" TOTALES GENERALES:   Procesadas: {total_gral}  |  Enviadas: {total_envio}  |  Vales Retenidos: {total_vales}", 1, 1, "C", True)
    
    return pdf.output(dest='S').encode('latin1')

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
                    res = supabase.table("usuarios")\
                        .select("*")\
                        .eq("nombre", usuario_input)\
                        .eq("password", password_input)\
                        .execute()
                    
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
        
        tab1, tab2, tab3 = st.tabs(["➕ Crear Nuevo Usuario", "📋 Listar / Modificar Usuarios", "📜 Historial de Lotes"])
        
        with tab1:
            st.subheader("Alta de Nuevo Usuario")
            with st.form("form_crear_usuario"):
                nuevo_nombre = st.text_input("Nombre de Usuario")
                nueva_pass = st.text_input("Contraseña", type="password")
                nuevo_rol = st.selectbox("Rol / Función", ["Sucursal", "Mutual", "Administrador"])
                
                submitted = st.form_submit_button("Crear Usuario", type="primary")
                if submitted:
                    if nuevo_nombre and nueva_pass:
                        try:
                            supabase.table("usuarios").insert({
                                "nombre": nuevo_nombre,
                                "password": nueva_pass,
                                "rol": nuevo_rol
                            }).execute()
                            st.success(f"¡Usuario '{nuevo_nombre}' creado con éxito!")
                        except Exception as e:
                            st.error(f"Error al crear el usuario: {e}")
                    else:
                        st.warning("Completá todos los campos obligatorios.")

        with tab2:
            st.subheader("Usuarios Registrados en el Sistema")
            try:
                res_usuarios = supabase.table("usuarios").select("id, nombre, rol").execute()
                usuarios_lista = res_usuarios.data
                
                if usuarios_lista:
                    for u in usuarios_lista:
                        with st.expander(f"👤 {u['nombre']} (Rol: {u['rol']})"):
                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                with st.form(f"form_edit_{u['id']}"):
                                    st.write("Modificar datos")
                                    edit_pass = st.text_input("Nueva Contraseña (opcional)", type="password", key=f"pass_{u['id']}")
                                    edit_rol = st.selectbox("Nuevo Rol", ["Sucursal", "Mutual", "Administrador"], index=["Sucursal", "Mutual", "Administrador"].index(u['rol']) if u['rol'] in ["Sucursal", "Mutual", "Administrador"] else 0, key=f"rol_{u['id']}")
                                    
                                    if st.form_submit_button("Guardar Cambios"):
                                        try:
                                            update_data = {"rol": edit_rol}
                                            if edit_pass:
                                                update_data["password"] = edit_pass
                                            
                                            supabase.table("usuarios").update(update_data).eq("id", u['id']).execute()
                                            st.success("¡Usuario actualizado correctamente!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error al actualizar: {e}")
                            
                            with col_b:
                                st.write("Zona de Peligro")
                                if u['nombre'] == user.get('nombre'):
                                    st.info("No podés eliminar tu propia cuenta activa.")
                                else:
                                    if st.button("🗑️ Eliminar Usuario", key=f"del_{u['id']}"):
                                        try:
                                            supabase.table("usuarios").delete().eq("id", u['id']).execute()
                                            st.success(f"Usuario {u['nombre']} eliminado.")
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
                res_lotes_admin = supabase.table("lotes").select("*").order("created_at", desc=True).execute()
                if res_lotes_admin.data:
                    df_h_admin = pd.DataFrame(res_lotes_admin.data)
                    st.dataframe(
                        df_h_admin[["id_lote", "sucursal", "fecha_carga", "estado", "observacion", "created_at"]],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Aún no se han registrado lotes en la base de datos.")
            except Exception as e:
                st.error(f"Error al recuperar el historial: {e}")
        
    elif rol == "sucursal":
        st.header("🏪 Panel de Sucursal - Control y Generación de Lotes")
        
        tab_cierre, tab_historial = st.tabs(["🔒 Cierre de Lote", "📜 Historial de Lotes"])
        
        with tab_cierre:
            # Si ya se generó un lote con éxito
            if "lote_generado_exito" in st.session_state:
                lote_info = st.session_state["lote_generado_exito"]
                st.success(f"¡Lote del día **{lote_info['fecha']}** guardado y cerrado con éxito en Supabase!")
                st.markdown("---")
                st.subheader("📄 Resumen y Comprobante para Mutuales")
                st.info(f"Resumen: {lote_info['total_envio']} recetas enviadas a mutuales | {lote_info['total_vales']} recetas retenidas como vales.")
                
                pdf_bytes = generar_pdf_bytes(
                    user.get("nombre", "Sucursal"),
                    lote_info['fecha'],
                    lote_info['referencia'],
                    lote_info['total_envio'],
                    lote_info['total_vales'],
                    lote_info.get("resumen_os", pd.DataFrame()),
                    lote_info.get("df_vales", pd.DataFrame())
                )
                
                st.download_button(
                    label="📥 Descargar Resumen en PDF",
                    data=pdf_bytes,
                    file_name=f"Resumen_Lote_{lote_info['fecha'].replace('/', '-')}.pdf",
                    mime="application/pdf",
                    type="primary"
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
                    fecha_recetas = st.date_input("📅 Fecha correspondiente a las recetas")
                with col_reset:
                    st.write("")
                    st.write("")
                    if st.button("🔄 Reiniciar Datos", help="Limpia la selección de vales y restablece los valores"):
                        u_actual = st.session_state.get("usuario_logueado")
                        st.session_state.clear()
                        st.session_state["usuario_logueado"] = u_actual
                        st.rerun()

                fecha_str_db = fecha_recetas.strftime("%Y-%m-%d")
                fecha_str_fmt = fecha_recetas.strftime("%d/%m/%Y")
                sucursal_actual = user.get("nombre", "Sucursal")

                lote_existente = None
                try:
                    res_check = supabase.table("lotes")\
                        .select("*")\
                        .eq("sucursal", sucursal_actual)\
                        .eq("fecha_carga", fecha_str_db)\
                        .execute()
                    
                    if res_check.data and len(res_check.data) > 0:
                        lote_existente = res_check.data[0]
                except Exception as e:
                    pass

                if lote_existente:
                    st.warning(f"⚠️ **ATENCIÓN:** Ya existe un lote registrado para la sucursal **{sucursal_actual}** con la fecha **{fecha_str_fmt}**.")
                    st.info(f"**Identificador previo:** `{lote_existente.get('id_lote')}` | **Observación:** {lote_existente.get('observacion')}")
                    
                    col_eliminar, col_seguir = st.columns(2)
                    with col_eliminar:
                        if st.button("🗑️ Eliminar Lote Existente y Continuar", type="secondary"):
                            try:
                                supabase.table("lotes").delete().eq("id_lote", lote_existente.get('id_lote')).execute()
                                st.success("¡Lote anterior eliminado con éxito! Ya podés continuar cargando.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al eliminar el lote: {e}")
                    with col_seguir:
                        st.info("*(O seleccioná otra fecha arriba si preferís no borrarlo)*")