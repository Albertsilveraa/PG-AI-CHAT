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

class UserQueryAgent:
    """
    Este agente recibe la pregunta del usuario y la transforma
    en una estructura JSON/Dict con intención, entidad y posibles filtros.
    """
    def __init__(self, llm, schema_agent):
        self.llm = llm
        self.schema_agent = schema_agent

    def interpret(self, question):
        """
        Usa un LLM para analizar la intención del usuario
        y retorna un dict con la estructura de la consulta.
        """
        prompt_template = """
        Con base en el siguiente esquema de la base de datos:
        {schema}

        Interpreta la pregunta del usuario y describe su intención en formato JSON:
        - "intencion": la acción (contar, listar, detallar, etc.)
        - "tabla": la tabla principal
        - "filtros": un objeto con columna: valor para filtrar (puede estar vacío)

        Pregunta: {question}
        """
        schema_text = self.schema_agent.get_schema_text()

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["schema", "question"]
        )
        chain = LLMChain(llm=self.llm, prompt=prompt)

        raw_response = chain.run(schema=schema_text, question=question).strip()

        # Intentar parsear el raw_response como JSON
        try:
            query_structure = json.loads(raw_response)
        except json.JSONDecodeError:
            # Si falla, usamos un default
            query_structure = {
                "intencion": "desconocida",
                "tabla": None,
                "filtros": {}
            }

        return query_structure

class SQLQueryGenerationAgent:
    """
    Agente que genera consultas SQL basadas en la estructura de consulta interpretada.
    """
    def __init__(self, llm, schema_agent):
        self.llm = llm
        self.schema_agent = schema_agent

    def generate_sql_query(self, query_structure):
        """
        Genera una consulta SQL basada en la estructura de consulta interpretada.
        """
        prompt_template = """
        Con base en el siguiente esquema de la base de datos:
        {schema}

        Genera una consulta SQL para la siguiente estructura de consulta:
        Intención: {intencion}
        Tabla: {tabla}
        Filtros: {filtros}

        SQL Query:
        """
        schema_text = self.schema_agent.get_schema_text()

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["schema", "intencion", "tabla", "filtros"]
        )
        chain = LLMChain(llm=self.llm, prompt=prompt)

        sql_query = chain.run(
            schema=schema_text, 
            intencion=query_structure.get("intencion", ""),
            tabla=query_structure.get("tabla", ""),
            filtros=json.dumps(query_structure.get("filtros", {}))
        ).strip()

        return sql_query

class NaturalLanguageResponseAgent:
    """
    Agente que convierte resultados de consultas SQL en respuestas en lenguaje natural.
    """
    def __init__(self, llm):
        self.llm = llm

    def generate_response(self, query_structure, sql_result):
        """
        Genera una respuesta en lenguaje natural basada en los resultados de la consulta.
        """
        prompt_template = """
        Basado en la estructura de consulta original y los resultados de la consulta SQL:

        Estructura de Consulta: {query_structure}
        Resultados de la Consulta: {sql_result}

        Genera una respuesta en lenguaje natural concisa y clara que responda la pregunta original.

        Respuesta en Lenguaje Natural:
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["query_structure", "sql_result"]
        )
        chain = LLMChain(llm=self.llm, prompt=prompt)

        natural_response = chain.run(
            query_structure=json.dumps(query_structure),
            sql_result=str(sql_result)
        ).strip()

        return natural_response

class QueryOrchestrator:
    """
    Orquestador que coordina los tres agentes para procesar consultas de usuario.
    """
    def __init__(self, llm, schema_agent):
        self.user_query_agent = UserQueryAgent(llm, schema_agent)
        self.sql_query_agent = SQLQueryGenerationAgent(llm, schema_agent)
        self.natural_language_agent = NaturalLanguageResponseAgent(llm)

    def process_query(self, question):
        """
        Procesa una consulta de usuario pasándola por los tres agentes.
        """
        # Paso 1: Interpretación de la consulta
        query_structure = self.user_query_agent.interpret(question)

        # Paso 2: Generación de consulta SQL
        sql_query = self.sql_query_agent.generate_sql_query(query_structure)

        # Paso 3: Ejecución de consulta SQL (esto dependerá de tu implementación de conexión)
        sql_result = self.execute_sql_query(sql_query)

        # Paso 4: Generación de respuesta en lenguaje natural
        natural_response = self.natural_language_agent.generate_response(query_structure, sql_result)

        return {
            "query_structure": query_structure,
            "sql_query": sql_query,
            "sql_result": sql_result,
            "natural_response": natural_response
        }

    def execute_sql_query(self, sql_query):
        """
        Método para ejecutar consultas SQL. 
        NOTA: Debes implementar la lógica de conexión y ejecución según tu entorno.
        """
        # Implementación de ejemplo
        connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchall()
            return result
        finally:
            connection.close()