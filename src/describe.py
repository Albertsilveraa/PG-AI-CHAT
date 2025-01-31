import os
import re
import pymysql
import pandas as pd
from dotenv import load_dotenv
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json

class SQLGenerationAgent:
    """
    Genera sentencias SQL a partir de la estructura interpretada.
    Soporta generación de SQL mediante LLM.
    """
    def __init__(self, llm, schema_agent):
        self.llm = llm
        self.schema_agent = schema_agent

    def generate_sql(self, query_structure):
        """
        Genera consulta SQL usando LLM o método tradicional.
        """
        intent = query_structure.get("intencion", "").lower()
        table = query_structure.get("tabla", "")
        filters = query_structure.get("filtros", {})

        if not table:
            return "Lo siento, no se identificó la tabla en la base de datos."

        # Prompt template para generación de SQL con LLM
        prompt_template = """
        Esquema de Base de Datos: {schema}
        
        Información de la Consulta:
        - Intención: {intention}
        - Tabla: {table}
        - Filtros: {filters}

        Genera una consulta SQL precisa considerando:
        1. La intención específica
        2. Nombres correctos de tablas y columnas
        3. Filtrado apropiado
        4. Limitar resultados a 25 si no se especifica lo contrario

        Devuelve SOLO la consulta SQL, sin texto adicional.
        """

        # Obtener esquema de la base de datos
        schema_text = self.schema_agent.get_schema_text()

        # Configurar prompt para LLM
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["schema", "intention", "table", "filters"]
        )
        
        # Crear cadena con LLM
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # Generar consulta SQL
        try:
            sql_query = chain.run(
                schema=schema_text,
                intention=intent,
                table=table,
                filters=json.dumps(filters)
            ).strip()

            # Añadir punto y coma si no existe
            if not sql_query.endswith(';'):
                sql_query += ';'

            return sql_query
        except Exception as e:
            return f"Error al generar SQL: {str(e)}"