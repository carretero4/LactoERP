import db_funciones
import secrets

if __name__ == "__main__":
    #secret_key = secrets.token_hex(64)
    #print(secret_key)
    print("Iniciando la configuración de la aplicación...")
    db_funciones.setup_database_and_user()
    print("Proceso de configuración finalizado.")