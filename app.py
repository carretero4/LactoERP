# LactoERP/app.py

import streamlit as st
import db_funciones 

# --- Función para cerrar sesión ---
def logout_user():
    # Eliminar el token de la DB si existe en la URL
    current_token = st.query_params.get('session_token')
    if current_token:
        db_funciones.delete_session_token(current_token)
    
    st.session_state['authenticated'] = False
    st.session_state['username'] = None
    st.session_state['user_id'] = None
    st.session_state['remember_me_checkbox_state'] = False # Resetear al cerrar sesión
    st.query_params.clear() # Limpiar el parámetro de la URL al cerrar sesión
   # st.rerun() # Fuerza una recarga

# --- Función para intentar login ---
def login_attempt(username, password, remember_me):
    user_id = db_funciones.verify_user_password(username, password)
    if user_id:
        st.session_state['authenticated'] = True
        st.session_state['username'] = username
        st.session_state['user_id'] = user_id
        st.session_state['remember_me_checkbox_state'] = remember_me # Guardar la preferencia
        st.success(f"¡Bienvenido, {username}!")
        
        if remember_me:
            # Generar y guardar un token de sesión
            token = db_funciones.generate_session_token(user_id)
            if token:
                st.query_params['session_token'] = token # Añadir el token a la URL
                st.info("Sesión iniciada. Se mantendrá persistente a través del token en la URL.")
            else:
                st.error("No se pudo generar el token de sesión. La persistencia fallará.")
        else:
            # Si no quiere persistencia, asegurar que no haya token en la URL
            if 'session_token' in st.query_params:
                del st.query_params['session_token']
            st.info("Sesión iniciada. Se cerrará al cerrar la pestaña del navegador.")
            
        st.rerun() # Fuerza una recarga
    else:
        st.error("Usuario o contraseña incorrectos.")


# --- Configuración de la página ---
st.set_page_config(page_title="Lacto ERP - Login", layout="centered")

# --- Control de estado de sesión para autenticación ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'user_id' not in st.session_state: # Nuevo: para almacenar el ID del usuario
    st.session_state['user_id'] = None
if 'remember_me_checkbox_state' not in st.session_state:
    st.session_state['remember_me_checkbox_state'] = False # Estado del checkbox

# --- Lógica de persistencia al inicio de la aplicación ---
# SOLO intenta restaurar la sesión si no estamos ya autenticados.
if not st.session_state['authenticated']:
    session_token = st.query_params.get('session_token')
    if session_token:
        print(f"DEBUG: app.py - Token de sesión encontrado en URL: {session_token[:10]}...")
        user_id_from_token = db_funciones.verify_session_token(session_token)
        if user_id_from_token:
            st.session_state['authenticated'] = True
            st.session_state['user_id'] = user_id_from_token
            st.session_state['username'] = db_funciones.get_username_by_id(user_id_from_token)
            print(f"DEBUG: app.py - Sesión restaurada para usuario: {st.session_state['username']}")
            st.success(f"¡Bienvenido de nuevo, {st.session_state['username']}!")
            # No se hace rerun aquí, se dejará que el flujo normal de Streamlit renderice el contenido autenticado.
        else:
            print("DEBUG: app.py - Token de sesión inválido o caducado. Limpiando URL.")
            st.query_params.clear() # Limpiar token inválido de la URL
            st.warning("Su sesión ha caducado o es inválida. Por favor, inicie sesión de nuevo.")
            st.rerun() # Forzar rerun para limpiar la URL y mostrar el login



# --- Contenido principal de la aplicación o formulario de login ---
if st.session_state['authenticated']:
    # Contenido de la aplicación una vez logueado
    st.sidebar.button('Cerrar Sesión', on_click=logout_user)
    
    st.title('Panel de Control ERP Letra Q')
    st.write(f'¡Bienvenido, *{st.session_state["username"]}*!')
    st.write('Aquí iría el contenido principal de tu aplicación.')
    st.write('Por ejemplo, un dashboard, opciones de menú, etc.')

else:
    # --- CENTRAR IMAGEN DEL LOGO Y TÍTULO PRINCIPAL DEL LOGIN ---
    col1, col2, col3 = st.columns([1, 2, 1]) 
    with col2:
        st.image('imagenes/logos/logo_casa.png', use_container_width=True) 
    
    # Formulario de login
    with st.form("login_form"):
        username_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password")
        
        # Checkbox "Mantener sesión iniciada"
        remember_me_checkbox = st.checkbox(
            "Mantener sesión iniciada", 
            value=st.session_state['remember_me_checkbox_state'] # Mantiene el estado del checkbox
        ) 
        
        submit_button = st.form_submit_button("Iniciar Sesión")

        if submit_button:
            login_attempt(username_input, password_input, remember_me_checkbox) 

    st.warning('Por favor, introduce tu usuario y contraseña para acceder.')