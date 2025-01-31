import os
import re
import pymysql
import pandas as pd
from dotenv import load_dotenv
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
from conection import *
from semanticmap import *
from interpretation import *
from describe import * 

load_dotenv()

# =========================================================
# AGENTE 5: Ejecución de la consulta
# =========================================================
class QueryExecutionAgent:
    """
    Ejecuta la consulta SQL en la base de datos y retorna los resultados.
    """
    def __init__(self, get_connection):
        self.get_connection = get_connection

    def execute_query(self, sql_query):
        """
        Ejecuta la sentencia SQL y retorna un dict con la info:
        {
          "success": bool,
          "data": pd.DataFrame (o None),
          "message": str
        }
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql_query)
            # Si es SELECT, retornamos las filas
            if sql_query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df = pd.DataFrame(rows, columns=columns)
                return {"success": True, "data": df, "message": ""}
            else:
                # Para INSERT, UPDATE, DELETE, etc.
                conn.commit()
                return {"success": True, "data": None, "message": "Operación ejecutada correctamente"}
        except Exception as e:
            return {"success": False, "data": None, "message": str(e)}
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass


# =========================================================
# CLASE PRINCIPAL: SQLBot (Orquestador)
# =========================================================
class SQLBot:
    """
    Clase principal que inicializa y coordina todos los agentes
    para convertir las preguntas en consultas SQL y ejecutar resultados.
    """
    def __init__(self):
        # Leer variables de entorno
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.db_name = os.getenv("DB_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "3306")

        # Inicializar LLM
        self.llm = OpenAI(api_key=self.openai_api_key, temperature=0)

        # Función de conexión
        def get_connection():
            return pymysql.connect(
                host=self.db_host,
                port=int(self.db_port),
                user=self.db_user,
                password=self.db_password,
                db=self.db_name,
                cursorclass=pymysql.cursors.Cursor
            )

        # Inicializar Agentes
        self.schema_agent = DatabaseSchemaAgent(get_connection, self.db_name)
        self.semantic_agent = SemanticMappingAgent(self.schema_agent)
        self.user_query_agent = UserQueryAgent(self.llm, self.schema_agent)
        self.sql_generation_agent = SQLGenerationAgent(llm=self.llm,  # Add LLM parameter
    schema_agent=self.schema_agent)
        self.execution_agent = QueryExecutionAgent(get_connection)
         

    # --------------------------------------------
    # Métodos de configuración
    # --------------------------------------------
    def update_credentials(self, api_key=None, db_name=None, db_user=None, 
                           db_password=None, db_host=None, db_port=None):
        """Actualiza las credenciales de la base de datos y/o LLM."""
        if api_key:
            self.openai_api_key = api_key
            self.llm = OpenAI(api_key=self.openai_api_key, temperature=0)

        if db_name: self.db_name = db_name
        if db_user: self.db_user = db_user
        if db_password: self.db_password = db_password
        if db_host: self.db_host = db_host
        if db_port: self.db_port = db_port

        # Reinicializar Agentes con las nuevas credenciales
        def get_connection():
            return pymysql.connect(
                host=self.db_host,
                port=int(self.db_port),
                user=self.db_user,
                password=self.db_password,
                db=self.db_name,
                cursorclass=pymysql.cursors.Cursor
            )

        self.schema_agent = DatabaseSchemaAgent(get_connection, self.db_name)
        self.semantic_agent = SemanticMappingAgent(self.schema_agent)
        self.user_query_agent = UserQueryAgent(self.llm, self.schema_agent)
        self.sql_generation_agent = SQLGenerationAgent(llm=self.llm, schema_agent=self.schema_agent)
        self.execution_agent = QueryExecutionAgent(get_connection)

    # --------------------------------------------
    # Métodos de utilería
    # --------------------------------------------
    def get_schema(self):
        """Retorna el esquema en texto (para debug o mostrar en UI)."""
        return self.schema_agent.get_schema_text()

    def initialize_database(self):
        """
        Crea tablas de ejemplo si no existen (opcional),
        útil para pruebas o bases de datos vacías.
        """
        def get_connection():
            return pymysql.connect(
                host=self.db_host,
                port=int(self.db_port),
                user=self.db_user,
                password=self.db_password,
                db=self.db_name,
                cursorclass=pymysql.cursors.Cursor
            )
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    edad INT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)
            cursor.execute("SELECT COUNT(*) FROM usuarios;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO usuarios (nombre, email, edad) VALUES
                    ('Usuario 1', 'usuario1@example.com', 25),
                    ('Usuario 2', 'usuario2@example.com', 30),
                    ('Usuario 3', 'usuario3@example.com', 35);
                """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    # --------------------------------------------
    # PIPELINE PRINCIPAL
    # --------------------------------------------
    def process_query(self, question: str):
        """
        Pipeline completo: 
        1) Interpreta la pregunta
        2) Genera SQL
        3) Ejecuta la consulta
        4) Retorna el resultado
        """
        # 1) Interpretación
        interpreted = self.user_query_agent.interpret(question)

        # Verificar si la intención está relacionada con la BD
        if not interpreted.get("tabla"):
            return {
                "success": True, 
                "message": "Lo siento, solo respondo consultas de base de datos.", 
                "is_query": False
            }

        # 2) Generar SQL
        sql_query = self.sql_generation_agent.generate_sql(interpreted)

        if sql_query.startswith("Lo siento"):
            return {
                "success": True,
                "message": sql_query,
                "is_query": False
            }

        # 3) Ejecutar la consulta
        result = self.execution_agent.execute_query(sql_query)

        # Estructurar la respuesta final
        if result["success"]:
            response = {
                "success": True,
                "sql_query": sql_query,
                "is_query": True
            }
            if result["data"] is not None and not result["data"].empty:
                response["data"] = result["data"]
            if result["message"]:
                response["message"] = result["message"]
            return response
        else:
            return {
                "success": False,
                "error": result["message"]
            }

    # --------------------------------------------
    # Métodos individuales para frontend (opcional)
    # --------------------------------------------
    def interpret_user_query(self, question: str):
        return self.user_query_agent.interpret(question)

    def generate_sql(self, query_structure: dict):
        return self.sql_generation_agent.generate_sql(query_structure)

    def execute_query(self, sql_query: str):
        return self.execution_agent.execute_query(sql_query)
