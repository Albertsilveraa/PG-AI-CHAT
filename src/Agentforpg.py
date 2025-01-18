import os
import psycopg2
from dotenv import load_dotenv
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

load_dotenv()

# Variables de entorno para OpenAI y PostgreSQL
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

llm = OpenAI(
    api_key=OPENAI_API_KEY,
    temperature=0
)

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Crea la tabla usuarios si no existe  
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        edad INTEGER
    );
    """)

    # Verifica si la tabla está vacía
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

    # Obtiene nombres de tablas en el esquema público
    cursor.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    """)
    tables = cursor.fetchall()

    if not tables:
        cursor.close()
        conn.close()
        return {}

    schema = {}
    for (table_name,) in tables:
        cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s;
        """, (table_name,))
        columns = cursor.fetchall()
        schema[table_name] = columns

    cursor.close()
    conn.close()
    return schema

def execute_sql_query(query: str):
    conn = get_connection()
    cursor = conn.cursor()

    results = None
    try:
        # Verificar si la consulta es una definición de función
        query_upper = query.strip().upper()
        if query_upper.startswith("CREATE FUNCTION") or query_upper.startswith("CREATE OR REPLACE FUNCTION"):
            cursor.execute(query)
            conn.commit()
            results = "Función creada con éxito."
        else:
            # Dividir declaraciones múltiples separadas por punto y coma
            statements = [stmt.strip() for stmt in query.split(';') if stmt.strip()]
            for stmt in statements:
                cursor.execute(stmt)
                # Si la consulta es un SELECT, obtener resultados
                if stmt.upper().startswith("SELECT"):
                    results = cursor.fetchall()
            conn.commit()

            if results is None:
                results = "Operación realizada con éxito."
    except Exception as e:
        conn.rollback()
        results = f"Error al ejecutar la consulta: {e}"
    finally:
        cursor.close()
        conn.close()

    return results

prompt_template = """
Eres un asistente llamado SQLBOT que convierte consultas en lenguaje natural a consultas SQL, sentencias en lenguaje procedural PL/pgSQL o llamadas a funciones almacenadas en PostgreSQL.
La base de datos tiene las siguientes tablas y columnas:

{schema}

COMPORTAMIENTO:
1. Si la pregunta del usuario NO está directamente relacionada con la información o datos de la base de datos,
   responde de forma abierta y amigable, como todo un asistente que puede orientar o conversar sobre cualquier tema.

2. Si la pregunta del usuario está relacionada con la base de datos (por ejemplo, pedir información sobre usuarios),
   entonces:
   - Decide si una consulta SQL estándar es suficiente, si se requiere una sentencia procedural en PL/pgSQL o si es necesario llamar a una función almacenada existente.
   - Si es una consulta SQL estándar, genera una consulta SQL válida y sintácticamente correcta para PostgreSQL.
   - Si se requiere una sentencia procedural, genera una función o procedimiento en PL/pgSQL que cumpla con la tarea solicitada.
   - Si es una llamada a una función existente, genera la sentencia SQL para llamarla correctamente.
   - No agregues explicaciones de más; solo produce la consulta SQL, la sentencia PL/pgSQL o la llamada a la función.

3. Para describir la estructura de una tabla en PostgreSQL:
   - Utiliza: SELECT column_name, data_type FROM information_schema.columns WHERE table_name='nombre_tabla';
     o para ver la definición completa de la tabla: SELECT column_default, is_nullable, data_type FROM information_schema.columns WHERE table_name = 'nombre_tabla';

4. Para crear nuevas tablas o relacionarlas, usa CREATE TABLE o ALTER TABLE si es necesario.

5. Puedes usar declaraciones múltiples separadas por punto y coma (;) si la consulta, sentencia o llamada lo requiere.

Recuerda: Solo genera la consulta SQL, la sentencia PL/pgSQL o la llamada a la función si se relaciona directamente a la base de datos. De lo contrario, responde como asistente normal.

Pregunta: {question}
"""

def get_sql_query_from_natural_language(question: str, schema: dict) -> str:
    schema_str = "\n".join([
        f"Tabla: {table}\nColumnas: {', '.join([col[0] for col in columns])}"
        for table, columns in schema.items()
    ])

    prompt = PromptTemplate(
        input_variables=["schema", "question"],
        template=prompt_template
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.run(schema=schema_str, question=question)
    return response.strip()

def is_function_call(query: str) -> bool:
    
    function_call_keywords = ["SELECT", "CALL"]
    return any(query.strip().upper().startswith(keyword) for keyword in function_call_keywords)

def main():
    initialize_database()
    schema = get_tables_and_schema()

    if not schema:
        ("No se encontraron tablas en la base de datos. "
              "Por favor, verifica que la base de datos y sus tablas existan.")
        return

    ("\n¡Hola! Soy SQLBOT, tu asistente conectado a la base de datos con memoria de conversación.\n")
    ("Puedes hacerme preguntas en lenguaje natural   relacionadas a la BD, por ejemplo:")
    ("  - 'Muestra todos los usuarios con edad mayor de 30'")
    ("  - 'Insertar un nuevo usuario con nombre X, email Y y edad Z'")
    ("  - 'Describe la tabla usuarios'")
    ("  - 'Crea una tabla direcciones con relación a usuarios'")
    ("  - 'Crea una función para calcular el promedio de edad de los usuarios'")
    ("  - 'Llama a la función calcular_promedio_edad'")
    ("\nSi deseas terminar, escribe 'salir'.\n")

    while True:
        user_question = input("¿En qué puedo ayudarte?\n> ")
        if user_question.lower().strip() == "salir":
            ("\n¡Hasta luego! Gracias por usar mi servicio. :)\n")
            break

        answer = get_sql_query_from_natural_language(user_question, schema)

        # Si la respuesta no contiene una consulta SQL, sentencia PL/pgSQL o llamada a función, la mostramos directamente
        if not any(keyword in answer.upper() for keyword in ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "BEGIN", "END", "DECLARE", "PROCEDURE", "FUNCTION", "CALL")):
            ("\n", answer, "\n" + "-"*50 + "\n")
            continue

        ("\nConsulta/Sentencia/Procedimiento generado:")
        (answer)

        results = execute_sql_query(answer)

        # Verificar si la consulta generada es una llamada a una función
        if is_function_call(answer):
            # Si es una llamada a función, asumir que se espera un resultado
            ("\nResultados de la función:")
            if isinstance(results, str):
                (results)
            else:
                if results:
                    for row in results:
                        (row)
                else:
                    ("No se obtuvieron resultados (o la tabla puede estar vacía).")
        else:
            # Para consultas y sentencias estándar
            ("\nResultados:")
            if isinstance(results, str):
                (results)
            else:
                if results:
                    for row in results:
                        (row)
                else:
                    ("No se obtuvieron resultados (o la tabla puede estar vacía).")

        ("-"*50, "\n")

if __name__ == "__main__":
    main()
