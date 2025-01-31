import logging
import pandas as pd

class TableDataSummarizer:
    """
    Este agente construye un resumen con datos de ejemplo
    de cada tabla, para que el LLM tenga contexto real 
    y entienda mejor el significado de columnas y posibles valores.
    """
    def __init__(self, schema_agent, get_connection, max_rows=5):
        """
        :param schema_agent: Instancia de DatabaseSchemaAgent
        :param get_connection: Función que retorna una conexión a la BD
        :param max_rows: Número máximo de filas de ejemplo por tabla
        """
        self.schema_agent = schema_agent
        self.get_connection = get_connection
        self.max_rows = max_rows
        self.logger = logging.getLogger("TableDataSummarizer")

    def get_all_tables_summary(self):
        """
        Retorna un string que describe, para cada tabla:
          - Nombre de la tabla
          - Columnas
          - Ejemplos de datos (hasta max_rows filas)
        """
        schema_dict = self.schema_agent.get_schema_dict()
        summary_lines = []

        # Para cada tabla en el esquema
        for table_name, details in schema_dict.items():
            summary_lines.append(f"=== Tabla: {table_name} ===")

            # Columnas
            col_descriptions = []
            for col, info in details["columns"].items():
                col_descriptions.append(f"{col} ({info['type']})")
            cols_str = ", ".join(col_descriptions)
            summary_lines.append(f"Columnas: {cols_str}")

            # Muestras de datos
            sample_data_df = self._fetch_sample_data(table_name)
            if sample_data_df is not None and not sample_data_df.empty:
                summary_lines.append(f"Ejemplo de {self.max_rows} filas:")
                summary_lines.append(sample_data_df.to_string(index=False))
            else:
                summary_lines.append("No hay filas de ejemplo o la tabla está vacía.")

            summary_lines.append("-" * 60)

        return "\n".join(summary_lines)

    def _fetch_sample_data(self, table_name):
        """
        Retorna un DataFrame con hasta 'max_rows' filas de la tabla indicada.
        """
        try:
            conn = self.get_connection()
            query = f"SELECT * FROM {table_name} LIMIT {self.max_rows};"
            df = pd.read_sql(query, conn)
            return df
        except Exception as e:
            self.logger.error(f"No se pudo extraer datos de {table_name}: {e}")
            return None
        finally:
            if conn:
                conn.close()
