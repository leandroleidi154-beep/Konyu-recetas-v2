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
        
        tab1, tab2 = st.tabs(["➕ Crear Nuevo Usuario", "📋 Listar / Modificar / Eliminar"])
        
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
        
    elif rol == "sucursal":
        st.header("🏪 Panel de Sucursal - Control y Generación de Lotes")
        st.write("Seleccioná la fecha correspondiente a las recetas y subí el reporte CSV para realizar el control físico y marcar vales.")
        
        # Si ya se generó un lote con éxito, mostramos la opción de descarga y reinicio
        if "lote_generado_exito" in st.session_state:
            lote_info = st.session_state["lote_generado_exito"]
            st.success(f"¡Lote **{lote_info['nombre']}** guardado y cerrado con éxito en Supabase!")
            st.markdown("---")
            st.subheader("📄 Resumen y Comprobante para Mutuales")
            st.info(f"Resumen: {lote_info['total_envio']} recetas enviadas a mutuales | {lote_info['total_vales']} recetas retenidas como vales.")
            
            # Generación del PDF con manejo seguro de claves
            class PDF(FPDF):
                def header(self):
                    self.set_font("Arial", "B", 16)
                    self.cell(0, 10, "Resumen de Cierre de Lote", 0, 1, "C")
                    self.set_font("Arial", "B", 11)
                    sucursal_nombre = user.get("nombre", "Sucursal")
                    self.cell(0, 6, f"Sucursal: {sucursal_nombre}  |  Fecha de Recetas: {lote_info['fecha']}", 0, 1, "C")
                    self.set_font("Arial", "I", 10)
                    self.cell(0, 6, f"Referencia Lote: {lote_info['nombre']}", 0, 1, "C")
                    self.ln(5)
                    self.line(10, self.get_y(), 200, self.get_y())
                    self.ln(5)

                def footer(self):
                    self.set_y(-15)
                    self.set_font("Arial", "I", 8)
                    self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

            pdf = PDF()
            pdf.add_page()
            
            # 1. Cuadro de Resumen por Obra Social
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "1. Resumen por Obra Social (Recetas Enviadas)", 0, 1, "L")
            pdf.ln(2)
            
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(90, 7, "Obra Social", 1, 0, "L", True)
            pdf.cell(30, 7, "Total CSV", 1, 0, "C", True)
            pdf.cell(30, 7, "Vales Retenidos", 1, 0, "C", True)
            pdf.cell(40, 7, "A Enviar (Fisico)", 1, 1, "C", True)
            
            pdf.set_font("Arial", "", 9)
            df_os_resumen = lote_info.get("resumen_os", pd.DataFrame())
            if not df_os_resumen.empty:
                for _, row_os in df_os_resumen.iterrows():
                    os_txt = str(row_os["Obra Social"])[:45]
                    pdf.cell(90, 6, os_txt, 1, 0, "L")
                    pdf.cell(30, 6, str(row_os["Total"]), 1, 0, "C")
                    pdf.cell(30, 6, str(row_os["Vales"]), 1, 0, "C")
                    pdf.cell(40, 6, str(row_os["A Enviar"]), 1, 1, "C")
            else:
                pdf.cell(190, 6, "Detalle por obra social no disponible para esta sesión.", 1, 1, "C")
                
            pdf.ln(8)
            
            # 2. Cuadro de Vales Retenidos
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "2. Detalle de Vales Retenidos (Pendientes en Sucursal)", 0, 1, "L")
            pdf.ln(2)
            
            df_vales_det = lote_info.get("df_vales", pd.DataFrame())
            if not df_vales_det.empty:
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(60, 7, "Obra Social", 1, 0, "L", True)
                pdf.cell(45, 7, "Plan", 1, 0, "L", True)
                pdf.cell(42, 7, "Nro Ticket", 1, 0, "C", True)
                pdf.cell(43, 7, "T.T.", 1, 1, "C", True)
                
                pdf.set_font("Arial", "", 8)
                for _, row_v in df_vales_det.iterrows():
                    pdf.cell(60, 6, str(row_v["Obra Social"])[:30], 1, 0, "L")
                    pdf.cell(45, 6, str(row_v["Plan"])[:22], 1,
