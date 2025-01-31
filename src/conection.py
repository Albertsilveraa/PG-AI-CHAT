class DatabaseSchemaAgent:
    
    def __init__(self, get_connection, db_name):
        self.get_connection = get_connection
        self.db_name = db_name
        self.cached_schema = None  # Cache para evitar múltiples lecturas

    def get_schema_dict(self):
        if self.cached_schema:
            return self.cached_schema

        conn = self.get_connection()
        cursor = conn.cursor()

        schema_dict = {}

        try:
            # 1. Obtener las tablas en la base de datos
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s;
            """, (self.db_name,))
            tables = cursor.fetchall()

            for (table_name,) in tables:
                # 2. Obtener columnas y tipo de datos
                cursor.execute("""
                    SELECT column_name, data_type, column_key
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s;
                """, (self.db_name, table_name))
                columns_data = cursor.fetchall()

                # 3. Obtener relaciones (FK)
                cursor.execute("""
                    SELECT column_name, referenced_table_name, referenced_column_name
                    FROM information_schema.key_column_usage
                    WHERE table_schema = %s 
                      AND table_name = %s
                      AND referenced_table_name IS NOT NULL;
                """, (self.db_name, table_name))
                relations = cursor.fetchall()

                # Estructurar la info
                schema_dict[table_name] = {
                    "columns": {
                        col[0]: {
                            "type": col[1],
                            "key": col[2]  # 'PRI', 'MUL', etc.
                        } for col in columns_data
                    },
                    "relations": [
                        {
                            "column": rel[0],
                            "referenced_table": rel[1],
                            "referenced_column": rel[2]
                        }
                        for rel in relations
                    ]
                }

            self.cached_schema = schema_dict
            return schema_dict

        finally:
            cursor.close()
            conn.close()

    def get_schema_text(self):
       
        schema_dict = self.get_schema_dict()
        lines = []
        for table, details in schema_dict.items():
            lines.append(f"Tabla: {table}")
            col_descriptions = []
            for col, info in details["columns"].items():
                pk_label = "[PK]" if info["key"] == "PRI" else ""
                col_descriptions.append(f"{col} ({info['type']}{pk_label})")
            lines.append("Columnas: " + ", ".join(col_descriptions))

            # Relaciones (FK)
            for rel in details["relations"]:
                lines.append(
                    f"FK en {table}.{rel['column']} -> {rel['referenced_table']}.{rel['referenced_column']}"
                )
            lines.append("-" * 50)
        return "\n".join(lines)