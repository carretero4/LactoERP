# LactoERP/db_funciones.py

import psycopg2
import bcrypt
import os
import secrets # Para generar tokens seguros
from datetime import datetime, timedelta # Para manejar fechas de caducidad

#from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT, DB_SSLMODE

DB_CONFIG_FILE = 'db_config.json'

def get_db_credentials():
    """
    Obtiene las credenciales de la DB directamente de las variables de entorno.
    Estas variables de entorno serán los "Secrets" configurados en Streamlit Community Cloud.
    """
    # Usamos .get() con un valor por defecto None por si alguna variable no está configurada,
    # aunque Streamlit Community Cloud las requiere todas para el despliegue.
    return {
        'DB_HOST': os.getenv('DB_HOST'),
        'DB_NAME': os.getenv('DB_NAME'),
        'DB_USER': os.getenv('DB_USER'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD'),
        'DB_PORT': int(os.getenv('DB_PORT', 5432)), # El puerto puede tener un valor por defecto numérico
        'DB_SSLMODE': os.getenv('DB_SSLMODE', 'require') # El SSL mode puede tener un valor por defecto
    }

def get_db_connection():
    db_creds = get_db_credentials()
    try:
        conn = psycopg2.connect(
            host=db_creds['DB_HOST'],
            database=db_creds['DB_NAME'],
            user=db_creds['DB_USER'],
            password=db_creds['DB_PASSWORD'],
            port=db_creds['DB_PORT'],
            sslmode=db_creds['DB_SSLMODE']
        )
        print("DEBUG: get_db_connection - Conexión establecida exitosamente.")
        return conn
    except psycopg2.Error as e:
        print(f"ERROR: get_db_connection - Error al establecer la conexión a la base de datos: {e}")
        return None


def setup_database_and_user():
    """
    Establece la conexión a la base de datos, crea el rol 'administrador'
    y el usuario 'perecarretero' si no existen.
    """
    conn = None
    try:
        conn = get_db_connection() # Usamos la nueva función para obtener la conexión
        if conn is None:
            print("No se pudo conectar a la base de datos. Abortando setup.")
            return

        cur = conn.cursor()
        print("Conexión a la base de datos exitosa para setup.")

        # 2. Crear el rol 'administrador' si no existe
        admin_role_name = 'administrador'
        cur.execute("SELECT id_rol FROM Roles WHERE nombre_rol = %s;", (admin_role_name,))
        admin_role_id = cur.fetchone()

        if admin_role_id:
            admin_role_id = admin_role_id[0]
            print(f"El rol '{admin_role_name}' ya existe con ID: {admin_role_id}")
        else:
            cur.execute("INSERT INTO Roles (nombre_rol, descripcion) VALUES (%s, %s) RETURNING id_rol;",
                        (admin_role_name, 'Acceso completo al sistema ERP de Letra Q'))
            admin_role_id = cur.fetchone()[0]
            print(f"Rol '{admin_role_name}' creado con ID: {admin_role_id}")
        conn.commit()

        # 3. Generar el hash seguro para la contraseña de 'perecarretero'
        username = 'perecarretero'
        plain_password = "MiContrasenaDePere123!" # <--- ¡CAMBIA ESTO!
        hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        print(f"Contraseña de '{username}' hasheada.")

        # 4. Crear el usuario 'perecarretero' si no existe
        cur.execute("SELECT id_usuario FROM Usuarios WHERE nombre_usuario = %s;", (username,))
        user_exists = cur.fetchone()

        if user_exists:
            print(f"El usuario '{username}' ya existe.")
        else:
            cur.execute(
                "INSERT INTO Usuarios (nombre_usuario, password_hash, id_rol, activo) "
                "VALUES (%s, %s, %s, %s);",
                (username, hashed_password, admin_role_id, True)
            )
            print(f"Usuario '{username}' creado exitosamente y asignado al rol '{admin_role_name}'.")

        conn.commit()
        print("Configuración de la base de datos y usuario completada.")

    except psycopg2.Error as e:
        print(f"Error de base de datos en setup_database_and_user: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()




# --- ¡ FUNCIÓN DE VERIFICACIÓN! ---
def verify_user_password(username, plain_password):

    """
    Verifica una contraseña de texto plano contra el hash almacenado en la DB.
    Retorna True si es correcta, False en caso contrario o si el usuario no existe.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("ERROR: verify_user_password - No se pudo conectar a la base de datos.")
            return False

        cur = conn.cursor()
        # Obtener el hash de la contraseña para el usuario dado
        cur.execute("SELECT password_hash FROM Usuarios WHERE nombre_usuario = %s AND activo = TRUE;", (username,))
        result = cur.fetchone()

        if result:
            hashed_password = result[0]
            # Verificar la contraseña usando bcrypt
            if bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8')):
                print(f"DEBUG: verify_user_password - Contraseña verificada para {username}: CORRECTA.")
                return True
            else:
                print(f"DEBUG: verify_user_password - Contraseña incorrecta para {username}.")
                return False
        else:
            print(f"DEBUG: verify_user_password - Usuario '{username}' no encontrado o inactivo.")
            return False

    except psycopg2.Error as e:
        print(f"ERROR: verify_user_password - Error de base de datos al verificar usuario: {e}")
        return False
    finally:
        if conn:
            cur.close()
            conn.close()

def get_username_by_id(user_id):
    """
    Obtiene el nombre de usuario dado un user_id.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("ERROR: get_username_by_id - No se pudo conectar a la base de datos.")
            return None
        cur = conn.cursor()
        cur.execute("SELECT nombre_usuario FROM Usuarios WHERE id = %s;", (user_id,))
        result = cur.fetchone()
        if result:
            return result[0]
        return None
    except psycopg2.Error as e:
        print(f"ERROR: get_username_by_id - Error al obtener nombre de usuario por ID: {e}")
        return None
    finally:
        if conn:
            cur.close()
            conn.close()

def generate_session_token(user_id, expiry_days=30):
    """
    Genera un token de sesión seguro, lo guarda en la DB y retorna el token.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("ERROR: generate_session_token - No se pudo conectar a la base de datos.")
            return None

        cur = conn.cursor()
        token = secrets.token_urlsafe(64) # Genera un token URL-safe de 64 bytes (aprox. 86 caracteres)
        expiry_date = datetime.now() + timedelta(days=expiry_days)

        # Eliminar tokens antiguos para este usuario si existen (opcional, para limpieza)
        cur.execute("DELETE FROM user_sessions WHERE user_id = %s;", (user_id,))

        cur.execute("""
            INSERT INTO user_sessions (token, user_id, expiry_date)
            VALUES (%s, %s, %s);
        """, (token, user_id, expiry_date))
        conn.commit()
        print(f"DEBUG: Token de sesión generado y guardado para user_id {user_id}. Expira en {expiry_date}.")
        return token
    except psycopg2.Error as e:
        print(f"ERROR: generate_session_token - Error al guardar el token de sesión: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            cur.close()
            conn.close()

def verify_session_token(token):
    """
    Verifica un token de sesión. Si es válido y no ha caducado, retorna el user_id.
    De lo contrario, retorna None. También elimina tokens caducados.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("ERROR: verify_session_token - No se pudo conectar a la base de datos.")
            return None

        cur = conn.cursor()
        # Eliminar tokens caducados antes de la verificación para mantener la tabla limpia
        cur.execute("DELETE FROM user_sessions WHERE expiry_date < CURRENT_TIMESTAMP;")
        conn.commit()

        cur.execute("""
            SELECT user_id FROM user_sessions
            WHERE token = %s AND expiry_date > CURRENT_TIMESTAMP;
        """, (token,))
        result = cur.fetchone()

        if result:
            user_id = result[0]
            print(f"DEBUG: Token {token[:10]}... verificado exitosamente para user_id {user_id}.")
            return user_id
        else:
            print(f"DEBUG: Token {token[:10]}... inválido o caducado.")
            return None
    except psycopg2.Error as e:
        print(f"ERROR: verify_session_token - Error al verificar el token de sesión: {e}")
        return None
    finally:
        if conn:
            cur.close()
            conn.close()

def delete_session_token(token):
    """
    Elimina un token de sesión de la base de datos.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("ERROR: delete_session_token - No se pudo conectar a la base de datos.")
            return False
        cur = conn.cursor()
        cur.execute("DELETE FROM user_sessions WHERE token = %s;", (token,))
        conn.commit()
        print(f"DEBUG: Token {token[:10]}... eliminado de la DB.")
        return True
    except psycopg2.Error as e:
        print(f"ERROR: delete_session_token - Error al eliminar el token de sesión: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            cur.close()
            conn.close()