import json
import pymysql
from conection import DatabaseSchemaAgent  # Asegúrate de que el archivo se llame así

# Función para obtener la conexión a la base de datos con pymysql
def get_connection():
    return pymysql.connect(
        host="10.23.63.53",      # Cambia por tu host
        user="root",           # Cambia por tu usuario
        password="rootpassword",   # Cambia por tu contraseña
        database="dev",  # Cambia por tu base de datos
        cursorclass=pymysql.cursors.DictCursor  # Para obtener resultados en formato diccionario
    )

def main():
    db_name = "dev"  # Cambia por el nombre de tu BD
    agent = DatabaseSchemaAgent(get_connection, db_name)
    
    print("\n📌 **Esquema en Texto**:")
    print(agent.get_schema_text())  # Muestra el esquema en formato legible

    print("\n📌 **Esquema en JSON**:")
    schema_json = json.dumps(agent.get_schema_dict(), indent=4, ensure_ascii=False)
    print(schema_json)  # Imprime el esquema en JSON
    
    print("\n📌 **Primeras Filas en JSON**:")
    first_rows_json = json.dumps(agent.get_first_rows(), indent=4, ensure_ascii=False)
    print(first_rows_json)  # Muestra las primeras filas en JSON

    print("\n📌 **Esquema Compacto en JSON**:")
    compact_schema_json = json.dumps(agent.get_compact_schema(), indent=4, ensure_ascii=False)
    print(compact_schema_json)  # Muestra el esquema compacto en JSON

if __name__ == "__main__":
    main()
