import streamlit as st
from supabase import create_client, Client
import pandas as pd
import io

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
        st.header("🏪 Panel de Sucursal - Carga de Lotes y Recetas")
        st.write("Subí el reporte diario/periódico en formato CSV para procesar los vales y generar el lote.")
        
        archivo_subido = st.file_uploader("Seleccioná el archivo CSV de recetas", type=["csv"])
        
        if archivo_subido is not None:
            try:
                # Leer el archivo con codificación latin1 para respetar acentos y caracteres especiales
                contenido_bytes = archivo_subido.getvalue()
                texto_decodificado = contenido_bytes.decode('latin1')
                lineas = texto_decodificado.splitlines()
                
                datos_procesados = []
                obra_social_actual = "GENERAL"
                
                # Parseo inteligente bloque por bloque
                for i, linea in enumerate(lineas):
                    partes = [p.strip() for p in linea.split(';')]
                    
                    # Detectar si la línea es de Obra Social (ej: ;OSPSA  -SANIDAD-;;;;...)
                    if len(partes) > 1 and partes[1].startswith(";") or (len(partes[1]) > 0 and "VALID" in partes[1] or "OSPSA" in partes[1] or "PAMI" in partes[1]):
                        os_candidata = partes[1].strip('; ')
                        if os_candidata and not os_candidata.startswith("A") and os_candidata != "Mandataria:":
                            obra_social_actual = os_candidata

                    # Detectar si es una línea de datos de receta (empieza con el nombre del plan o contiene tickets con guion tipo 0990-...)
                    # Buscamos filas que contengan formato de ticket ej '0990-00043135'
                    for p in partes:
                        if "-" in p and len(p) == 13 and p[:4].isdigit():
                            # Encontramos un ticket, intentamos extraer la fila anterior o estructurada
                            # Busquemos filas de datos estandarizadas después de la cabecera "Plan;...;Nro Ticket;...;T.T"
                            pass

                # Parser simplificado y robusto basado en filas de datos reales
                filas_datos = []
                os_actual = "OBRA SOCIAL GENERAL"
                
                for linea in lineas:
                    cols = linea.split(';')
                    # Limpiamos celdas vacías
                    cols_limpias = [c.strip() for c in cols if c.strip() != '']
                    
                    if len(cols) > 1 and cols[1].startswith(';') == False and ('-' in cols[1] or 'OSPSA' in cols[1] or 'PAMI' in cols[1] or 'VALID' in cols[1] or 'BAGO' in cols[1] or 'ANDROMACO' in cols[1] or 'ISDIN' in cols[1] or 'CAVIAHUE' in cols[1] or 'GALDERMA' in cols[1] or 'BY DERM' in cols[1]):
                        texto_linea = cols[1].strip()
                        if "VALID." in texto_linea or "SANIDAD" in texto_linea or "PAGO" in texto_linea:
                            os_actual = texto_linea.replace(';', '').strip()

                    # Si la fila tiene un número de ticket con formato XXXX-XXXXXXXX
                    for idx_c, val_c in enumerate(cols):
                        if len(val_c) == 13 and val_c[:4].isdigit() and '-' in val_c:
                            # Posible ticket. El plan suele estar al principio de la fila y el T.T más adelante
                            plan_val = cols[0] if cols[0] != '' else 'PLAN GENERAL'
                            nro_ticket = val_c
                            # Buscar T.T (suele estar en la siguiente columna con datos)
                            tt_val = ""
                            for siguiente in cols[idx_c+1:]:
                                if len(siguiente) >= 10 and '-' in siguiente:
                                    tt_val = siguiente
                                    break
                            if not tt_val:
                                tt_val = "N/D"
                                
                            filas_datos.append({
                                "Obra Social": os_actual,
                                "Plan": plan_val,
                                "Nro Ticket": nro_ticket,
                                "T.T": tt_val
                            })
                            break

                if filas_datos:
                    df_resultado = pd.DataFrame(filas_datos)
                    # Eliminar duplicados si los hubiera
                    df_resultado = df_resultado.drop_duplicates(subset=["Nro Ticket"])
                    
                    st.success(f"¡Archivo procesado con éxito! Se detectaron {len(df_resultado)} recetas/vales.")
                    st.dataframe(df_resultado, use_container_width=True)
                    
                    st.markdown("---")
                    nombre_lote = st.text_input("Nombre / Referencia del Lote (ej: Lote Quincenal Octubre)")
                    
                    if st.button("💾 Guardar y Generar Lote para Mutuales", type="primary"):
                        if nombre_lote:
                            st.success(f"¡Lote '{nombre_lote}' generado correctamente con {len(df_resultado)} recetas!")
                            st.info("💡 Próximamente: Este lote quedará disponible para la auditoría de las mutuales.")
                        else:
                            st.warning("Por favor, ingresá un nombre o referencia para el lote.")
                else:
                    st.warning("No se pudieron extraer recetas automáticamente con este formato. Revisá que sea el reporte correcto.")
                    
            except Exception as e:
                st.error(f"Error al procesar el archivo CSV: {e}")
        
    elif rol == "mutual":
        st.header("🏥 Panel de Mutual / Obra Social")
        st.write("Bienvenido al módulo de auditoría de recetas y lotes enviados.")
        
    else:
        st.warning("El usuario actual no tiene un rol válido asignado en la base de datos.")
