import streamlit as st
from supabase import create_client, Client
import pandas as pd

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
        
        # Pestañas internas para el administrador
        tab1, tab2 = st.tabs(["➕ Crear Nuevo Usuario", "📋 Listar / Modificar / Eliminar"])
        
        # --- SECCIÓN 1: CREAR USUARIO ---
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
                            # Insertar en Supabase
                            supabase.table("usuarios").insert({
                                "nombre": nuevo_nombre,
                                "password": nueva_pass,
                                "rol": nuevo_rol
                            }).execute()
                            st.success(f"¡Usuario '{nuevo_nombre}' creado con éxito!")
                        except Exception as e:
                            st.error(f"Error al crear el usuario (¿Quizás el nombre ya existe?): {e}")
                    else:
                        st.warning("Completá todos los campos obligatorios.")

        # --- SECCIÓN 2: LISTAR, MODIFICAR Y ELIMINAR ---
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
                                # Modificar contraseña o rol
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
                                # Evitar que el admin se borre a sí mismo por accidente
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
        st.header("🏪 Panel de Sucursal")
        st.write("Bienvenido al módulo de gestión de lotes y vales.")
        
    elif rol == "mutual":
        st.header("🏥 Panel de Mutual / Obra Social")
        st.write("Bienvenido al módulo de auditoría de recetas.")
        
    else:
        st.warning("El usuario actual no tiene un rol válido asignado en la base de datos.")
