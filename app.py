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
        st.session_state["usuario_logueado"] = None
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
        
        col_fecha, col_reset = st.columns([3, 1])
        with col_fecha:
            fecha_recetas = st.date_input("📅 Fecha correspondiente a las recetas")
        with col_reset:
            st.write("")
            st.write("")
            if st.button("🔄 Reiniciar Datos", help="Limpia la selección de vales y restablece los valores"):
                st.session_state.pop("df_lote_activo", None)
                st.session_state.pop("archivo_actual", None)
                st.session_state.pop("lote_generado_exito", None)
                keys_to_del = [k for k in st.session_state.keys() if k.startswith("fisico_")]
                for k in keys_to_del:
                    st.session_state.pop(k, None)
                st.rerun()

        archivo_subido = st.file_uploader("Seleccioná el archivo CSV de recetas", type=["csv"])
        
        if archivo_subido is not None:
            if "archivo_actual" not in st.session_state or st.session_state.get("archivo_actual") != archivo_subido.name:
                st.session_state["archivo_actual"] = archivo_subido.name
                st.session_state.pop("df_lote_activo", None)
                st.session_state.pop("lote_generado_exito", None)
                keys_to_del = [k for k in st.session_state.keys() if k.startswith("fisico_")]
                for k in keys_to_del:
                    st.session_state.pop(k, None)

            try:
                if "df_lote_activo" not in st.session_state:
                    contenido_bytes = archivo_subido.getvalue()
                    texto_decodificado = contenido_bytes.decode('latin1')
                    lineas = texto_decodificado.splitlines()
                    
                    filas_datos = []
                    obra_social_actual = "GENERAL"
                    
                    for i, linea in enumerate(lineas):
                        cols = [c.strip() for c in linea.split(';')]
                        
                        if len(cols) > 1 and cols[1].startswith('A') and cols[1][1:].isdigit():
                            if i > 0:
                                linea_anterior = lineas[i - 1].split(';')
                                for col_ant in linea_anterior:
                                    c_limpia = col_ant.strip('; ')
                                    if c_limpia and not c_limpia.startswith('A') and "Mandataria" not in c_limpia:
                                        obra_social_actual = c_limpia
                                        break

                        for idx_c, val_c in enumerate(cols):
                            if len(val_c) == 13 and val_c[:4].isdigit() and '-' in val_c:
                                plan_val = cols[0] if cols[0] != '' else 'PLAN GENERAL'
                                nro_ticket = val_c
                                tt_val = ""
                                for siguiente in cols[idx_c+1:]:
                                    if len(siguiente) >= 10 and '-' in siguiente:
                                        tt_val = siguiente
                                        break
                                if not tt_val:
                                    tt_val = "N/D"
                                    
                                filas_datos.append({
                                    "Obra Social": obra_social_actual,
                                    "Plan": plan_val,
                                    "Nro Ticket": nro_ticket,
                                    "T.T": tt_val,
                                    "Es Vale": False
                                })
                                break

                    if filas_datos:
                        df_base = pd.DataFrame(filas_datos)
                        df_base.insert(0, 'ID_Fila', [f"REC_{i}" for i in range(len(df_base))])
                        st.session_state["df_lote_activo"] = df_base
                    else:
                        st.warning("No se pudieron extraer recetas automáticamente con este formato.")
                        st.stop()

                df_activo = st.session_state["df_lote_activo"]

                st.success(f"¡Reporte cargado correctamente para el día {fecha_recetas.strftime('%d/%m/%Y')}! Total de recetas detectadas: {len(df_activo)}")
                st.markdown("---")

                def actualizar_vales():
                    if "editor_vales" in st.session_state and "edited_rows" in st.session_state["editor_vales"]:
                        cambios = st.session_state["editor_vales"]["edited_rows"]
                        for idx_fila_vis, datos_edit in cambios.items():
                            if "Es Vale" in datos_edit:
                                if 'df_filtrado_temp' in st.session_state and idx_fila_vis < len(st.session_state['df_filtrado_temp']):
                                    id_real = st.session_state['df_filtrado_temp'].iloc[idx_fila_vis]["ID_Fila"]
                                    nuevo_estado = datos_edit["Es Vale"]
                                    st.session_state["df_lote_activo"].loc[st.session_state["df_lote_activo"]["ID_Fila"] == id_real, "Es Vale"] = nuevo_estado
                                    
                                    os_afectada = st.session_state["df_lote_activo"].loc[st.session_state["df_lote_activo"]["ID_Fila"] == id_real, "Obra Social"].values[0]
                                    df_os_temp = st.session_state["df_lote_activo"][st.session_state["df_lote_activo"]["Obra Social"] == os_afectada]
                                    nuevo_a_enviar = len(df_os_temp) - len(df_os_temp[df_os_temp["Es Vale"] == True])
                                    st.session_state[f"fisico_{os_afectada}"] = nuevo_a_enviar

                # 2. Resumen compacto horizontal con números destacados
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
                        c_os, c_tot, c_val, c_env, c_fis_label, c_fis_
