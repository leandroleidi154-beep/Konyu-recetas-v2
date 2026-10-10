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

# 3. Pantalla de inicio de sesión / Selección de Rol temporal
st.title("💊 Konyu Recetas")
st.sidebar.title("Navegación")

# Menú lateral para simular o verificar roles por ahora
rol_seleccionado = st.sidebar.selectbox(
    "Seleccionar Rol (Temporal)",
    ["Seleccionar...", "Administrador", "Sucursal", "Mutual"]
)

if rol_seleccionado == "Seleccionar...":
    st.info("Por favor, selecciona un rol en el menú lateral para ingresar al sistema.")
    
elif rol_seleccionado == "Administrador":
    st.header("Panel de Administrador")
    st.write("Acá vas a poder gestionar usuarios, lotes y ver reportes generales.")
    
    # Ejemplo rápido de consulta a Supabase para verificar conexión
    try:
        response = supabase.table("usuarios").select("*").execute()
        usuarios = response.data
        st.subheader("Usuarios registrados en la base:")
        if usuarios:
            st.dataframe(pd.DataFrame(usuarios))
        else:
            st.warning("No hay usuarios cargados todavía en la tabla 'usuarios'.")
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")

elif rol_seleccionado == "Sucursal":
    st.header("Panel de Sucursal")
    st.write("Acá las sucursales van a poder cargar lotes y gestionar sus vales.")

elif rol_seleccionado == "Mutual":
    st.header("Panel de Mutual / Obra Social")
    st.write("Acá las mutuales van a poder auditar y procesar los vales.")
