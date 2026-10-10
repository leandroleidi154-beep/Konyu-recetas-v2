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
        
        # 1. Selector de fecha de las recetas
        fecha_recetas = st.date_input("📅 Fecha correspondiente a las recetas")
        
        archivo_subido = st.file_uploader("Seleccioná el archivo CSV de recetas", type=["csv"])
        
        if archivo_subido is not None:
            try:
                # Procesar archivo CSV
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
                    
                    if "df_lote_activo" not in st.session_state or st.session_state.get("archivo_actual") != archivo_subido.name:
                        st.session_state["df_lote_activo"] = df_base
                        st.session_state["archivo_actual"] = archivo_subido.name

                    df_activo = st.session_state["df_lote_activo"]

                    st.success(f"¡Reporte cargado correctamente para el día {fecha_recetas.strftime('%d/%m/%Y')}! Total de recetas detectadas: {len(df_activo)}")
                    st.markdown("---")

                    # 2. Resumen compacto en una sola línea por Obra Social
                    st.subheader("📊 Control por Obra Social")
                    
                    obras_sociales = df_activo["Obra Social"].unique()
                    
                    if "fisico_inputs" not in st.session_state:
                        st.session_state["fisico_inputs"] = {}

                    for os_nombre in obras_sociales:
                        df_os = df_activo[df_activo["Obra Social"] == os_nombre]
                        total_csv = len(df_os)
                        vales_marcados = len(df_os[df_os["Es Vale"] == True])
                        a_enviar = total_csv - vales_marcados
                        
                        key_fisico = f"fisico_{os_nombre}"
                        if key_fisico not in st.session_state["fisico_inputs"]:
                            st.session_state["fisico_inputs"][key_fisico] = a_enviar
                        
                        # Renglón horizontal unificado
                        with st.container():
                            c_os, c_tot, c_val, c_env, c_fis, c_est = st.columns([2.5, 1, 1, 1, 1.5, 0.8])
                            
                            c_os.markdown(f"**{os_nombre}**")
                            c_tot.markdown(f"Total: `{total_csv}`")
                            c_val.markdown(f"Vales: `{vales_marcados}`")
                            c_env.markdown(f"A enviar: `{a_enviar}`")
                            
                            conteo_fisico = c_fis.number_input(
                                "Físico", 
                                min_value=0, 
                                max_value=total_csv,
                                value=min(st.session_state["fisico_inputs"][key_fisico], a_enviar), 
                                key=key_fisico,
                                label_visibility="collapsed"
                            )
                            st.session_state["fisico_inputs"][key_fisico] = conteo_fisico
                            
                            if conteo_fisico != a_enviar:
                                c_est.warning("⚠️")
                            else:
                                c_est.success("✅")
                            
                            st.markdown("---")

                    # 3. Listado detallado, buscador y marcado de Vales
                    st.subheader("🔍 Detalle de Recetas y Marcado de Vales")
                    
                    busqueda = st.text_input("🔎 Buscar por Nro de Ticket o T.T.", placeholder="Ej: 0990-00043135 o 9909-00558021")
                    
                    df_filtrado = df_activo.copy()
                    if busqueda:
                        df_filtrado = df_filtrado[
                            df_filtrado["Nro Ticket"].str.contains(busqueda, case=False, na=False) | 
                            df_filtrado["T.T"].str.contains(busqueda, case=False, na=False)
                        ]

                    st.info(f"Mostrando {len(df_filtrado)} de {len(df_activo)} registros.")

                    # Tabla interactiva con checkboxes para los vales
                    edited_df = st.data_editor(
                        df_filtrado[["ID_Fila", "Obra Social", "Plan", "Nro Ticket", "T.T", "Es Vale"]],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "ID_Fila": None,
                            "Es Vale": st.column_config.CheckboxColumn(
                                "Retener como Vale 🎫",
                                help="Tildá esta casilla si la receta queda retenida en la sucursal por falta de medicación.",
                                default=False,
                            )
                        },
                        key="editor_vales"
                    )

                    for index, row in edited_df.iterrows():
                        fila_id = row["ID_Fila"]
                        val_vale = row["Es Vale"]
                        df_activo.loc[df_activo["ID_Fila"] == fila_id, "Es Vale"] = val_vale

                    st.markdown("---")
                    
                    # 4. Botón de Generar Lote
                    nombre_lote = st.text_input("🏷️ Nombre / Referencia para cerrar el Lote (ej: Lote Sucursal 09 - 08/10/2026)")
                    
                    if st.button("🔒 Cerrar y Generar Lote para Mutuales", type="primary"):
                        if nombre_lote:
                            total_vales_lote = len(df_activo[df_activo["Es Vale"] == True])
                            total_envio_lote = len(df_activo) - total_vales_lote
                            st.success(f"¡Lote '{nombre_lote}' generado con éxito para la fecha {fecha_recetas.strftime('%d/%m/%Y')}!")
                            st.info(f"Resumen: {total_envio_lote} recetas enviadas a mutuales | {total_vales_lote} recetas retenidas como vales.")
                        else:
                            st.warning("Por favor, ingresá un nombre o referencia para identificar el lote.")
                else:
                    st.warning("No se pudieron extraer recetas automáticamente con este formato.")
                    
            except Exception as e:
                st.error(f"Error al procesar el archivo CSV: {e}")
        
    elif rol == "mutual":
        st.header("🏥 Panel de Mutual / Obra Social")
        st.write("Bienvenido al módulo de auditoría de recetas y lotes enviados.")
        
    else:
        st.warning("El usuario actual no tiene un rol válido asignado en la base de datos.")
