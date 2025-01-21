# backend.py
import os
import re
import psycopg2
import pandas as pd
from dotenv import load_dotenv
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

load_dotenv()

# ------------------------------------------------------------------------------
# VARIABLES DE ENTORNO
# ------------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

llm = OpenAI(api_key=OPENAI_API_KEY, temperature=0)

Data_base_Name = DB_NAME
Data_base_User = DB_USER
Data_base_Password = DB_PASSWORD
Data_base_Host = DB_HOST
Data_base_Port = DB_PORT

def update_credentials(api_key, db_name, db_user, db_password, db_host, db_port):
    """Actualiza credenciales globales para la conexión y el modelo LLM."""
    global OPENAI_API_KEY, llm
    global Data_base_Name, Data_base_User, Data_base_Password, Data_base_Host, Data_base_Port

    OPENAI_API_KEY = api_key or OPENAI_API_KEY
    Data_base_Name = db_name or Data_base_Name
    Data_base_User = db_user or Data_base_User
    Data_base_Password = db_password or Data_base_Password
    Data_base_Host = db_host or Data_base_Host
    Data_base_Port = db_port or Data_base_Port

    llm = OpenAI(api_key=OPENAI_API_KEY, temperature=0)

def get_connection():
    return psycopg2.connect(
        dbname=Data_base_Name,
        user=Data_base_User,
        password=Data_base_Password,
        host=Data_base_Host,
        port=Data_base_Port
    )

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        edad INTEGER
    );
    """)

    # Insertar datos de ejemplo si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM usuarios;")
    count = cursor.fetchone()[0]
    if count == 0:
        usuarios_ejemplo = [
            ("prueba 1", "prueba1@example.com", 30),
            ("prueba 2", "prueba2@example.com", 25),
            ("prueba 3", "prueba3@example.com", 40)
        ]
        insert_query = "INSERT INTO usuarios (nombre, email, edad) VALUES (%s, %s, %s);"
        cursor.executemany(insert_query, usuarios_ejemplo)
        conn.commit()

    cursor.close()
    conn.close()

def get_tables_and_schema() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public';
    """)
    tables = cursor.fetchall()

    if not tables:
        cursor.close()
        conn.close()
        return {}

    schema = {}
    relationships = {}

    for (table_name,) in tables:
        # Columnas
        cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s;
        """, (table_name,))
        columns = cursor.fetchall()
        schema[table_name] = columns

        # Claves foráneas
        cursor.execute("""
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name = %s;
        """, (table_name,))
        fkeys = cursor.fetchall()
        if fkeys:
            relationships[table_name] = fkeys

    cursor.close()
    conn.close()

    return {"tables": schema, "relationships": relationships}

def execute_sql_query(query: str):
    """
    Ejecuta cualquier consulta SQL (CREATE, INSERT, UPDATE, SELECT, etc.)
    Retorna:
      - Filas y columnas si es un SELECT.
      - Mensaje de éxito si no es SELECT.
      - Mensaje de error si falla.
    """
    conn = get_connection()
    cursor = conn.cursor()
    results = None

    try:
        # Dividir por ';' para soportar múltiples sentencias
        statements = [stmt.strip() for stmt in query.split(';') if stmt.strip()]
        for stmt in statements:
            cursor.execute(stmt)
            # Si la sentencia inicia con SELECT, tomamos resultados
            if stmt.upper().startswith("SELECT"):
                results = cursor.fetchall()

        conn.commit()

        if results is None:
            # Si no hubo un SELECT, operación exitosa
            results = "Operación realizada con éxito."
    except Exception as e:
        conn.rollback()
        results = f"Error al ejecutar la consulta: {e}"
    finally:
        cursor.close()
        conn.close()

    return results

def execute_sql_query_return_data(query: str):
    """
    Ejecuta el query y retorna (data, col_names) si es SELECT.
    Si no es SELECT, retorna (None, None) o lanza excepción en caso de error.
    """
    conn = get_connection()
    cursor = conn.cursor()
    data = None
    col_names = []

    try:
        statements = [stmt.strip() for stmt in query.split(';') if stmt.strip()]
        for stmt in statements:
            cursor.execute(stmt)
            if stmt.upper().startswith("SELECT"):
                data = cursor.fetchall()
                description = cursor.description
                if description:
                    col_names = [desc[0] for desc in description]
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

    return data, col_names

# Prompt ajustado para evitar "Respuesta:" o comentarios extra.
prompt_template = """
Eres un asistente llamado SQLBOT que convierte consultas en lenguaje natural a consultas SQL,
sentencias en lenguaje procedural PL/pgSQL o llamadas a funciones almacenadas en PostgreSQL.
La base de datos tiene las siguientes tablas y columnas:

{schema}

COMPORTAMIENTO:
1. Si la pregunta del usuario NO está relacionada con la información o datos de la base de datos,
   responde únicamente con un texto breve: "Lo siento, solo respondo consultas de base de datos."
2. Si la pregunta del usuario está relacionada con la base de datos, entonces:
   - Genera únicamente la consulta SQL o la sentencia PL/pgSQL correspondiente.
   - No incluyas explicaciones, texto adicional, ni el prefijo "Respuesta:".
3. Para describir la estructura de una tabla en PostgreSQL:
   SELECT column_name, data_type FROM information_schema.columns WHERE table_name='nombre_tabla';
4. Para crear nuevas tablas o relaciones, usa CREATE TABLE o ALTER TABLE.
5. Si es necesario, también puedes usar DO ... $$ ... $$ LANGUAGE plpgsql; para sentencias procedurales.

Pregunta: {question}
SALIDA: (SOLO el código SQL o PL/pgSQL)
"""

def get_sql_query_from_natural_language(question: str, schema_info: dict) -> str:
    """
    Dado un texto en lenguaje natural y la info del esquema, genera la consulta SQL (o PL/pgSQL).
    """
    tables = schema_info.get("tables", {})
    relationships = schema_info.get("relationships", {})

    # Construir string con la descripción de las tablas
    schema_str = "\n".join([
        f"Tabla: {table}\nColumnas: {', '.join([col[0] for col in columns])}"
        for table, columns in tables.items()
    ])

    # Agregar información sobre relaciones (claves foráneas)
    if relationships:
        rel_str = "\n".join([
            f"En {table}, la columna {col} referencia a {foreign_table}.{foreign_col}"
            for table, fkeys in relationships.items()
            for col, foreign_table, foreign_col in fkeys
        ])
        schema_str += "\nRelaciones:\n" + rel_str

    # Generamos el prompt final
    prompt = PromptTemplate(
        input_variables=["schema", "question"],
        template=prompt_template
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.run(schema=schema_str, question=question)

    # Posible limpieza de prefijos extra (por si el modelo insiste en ponerlos)
    cleaned_response = re.sub(r'(?i)\brespuesta:\s*', '', response).strip()

    return cleaned_response

# Cache local del esquema para no leer la DB en cada request
cached_schema = {}

def get_cached_schema():
    global cached_schema
    if cached_schema:
        return cached_schema
    schema_info = get_tables_and_schema()
    cached_schema = schema_info
    return schema_info

def create_df_from_sql(query: str) -> pd.DataFrame:
    """
    Ejecuta la consulta SQL y retorna un DataFrame de pandas con los resultados.
    """
    data, col_names = execute_sql_query_return_data(query)
    if data is None:
        raise ValueError("La consulta no devolvió resultados o no era un SELECT.")
    df = pd.DataFrame(data, columns=col_names)
    return df

def python_shell(code: str, context_vars: dict = None):
    """
    Ejecuta un fragmento de código Python en un entorno controlado.
    context_vars: dict con variables (DataFrames, etc.) disponibles dentro de code.
    Retorna lo que la variable 'output' contenga, si existe.
    """
    if context_vars is None:
        context_vars = {}

    local_vars = {}
    local_vars.update(context_vars)

    try:
        exec(code, {}, local_vars)
    except Exception as e:
        return f"Error al ejecutar el código Python: {e}"

    # Si el usuario define 'output' en su script, lo retornamos
    if "output" in local_vars:
        return local_vars["output"]

    return "Código ejecutado. (No se encontró la variable 'output'.)"
