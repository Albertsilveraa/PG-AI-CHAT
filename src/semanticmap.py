import re
import logging

class SemanticMappingAgent:
    """
    Este agente traduce (o “humaniza”) los nombres de tablas/columnas
    a términos más cercanos al lenguaje natural, y viceversa.
    Es opcional, pero útil si quieres hacer un mapeo semántico adicional.
    """

    def __init__(self, schema_agent):
        if not hasattr(schema_agent, 'get_schema_dict') or not callable(schema_agent.get_schema_dict):
            raise ValueError("El schema_agent debe ser una instancia válida con un método 'get_schema_dict'.")
        
        self.schema_agent = schema_agent
        self.map_cache = None

        # Configurar logging
        self.logger = logging.getLogger("SemanticMappingAgent")
        logging.basicConfig(level=logging.INFO)

    def build_semantic_map(self):
        """
        Crea un diccionario con equivalencias semánticas.
        Por ejemplo, 'car_color' -> ['color del carro', 'color'].
        """
        if self.map_cache:
            self.logger.info("Usando mapa semántico desde el caché.")
            return self.map_cache

        self.logger.info("Construyendo el mapa semántico.")
        try:
            schema_dict = self.schema_agent.get_schema_dict()
            semantic_map = {}

            for table, details in schema_dict.items():
                # Nombre de tabla "humanizado"
                semantic_map[table] = {
                    "human_name": self.humanize(table),
                    "columns": {}
                }
                for col in details["columns"].keys():
                    semantic_map[table]["columns"][col] = self.humanize(col)

            self.map_cache = semantic_map
            self.logger.info("Mapa semántico construido exitosamente.")
            return semantic_map

        except Exception as e:
            self.logger.error(f"Error al construir el mapa semántico: {e}")
            raise

    def humanize(self, name):
        """
        Convierte un nombre_de_tabla o nombre_de_columna en formato legible.
        Por ejemplo, 'nombre_de_tabla' -> 'Nombre de tabla'.
        """
        try:
            # Reemplazar caracteres especiales con espacios y capitalizar
            humanized = re.sub(r'[_-]', ' ', name).strip().capitalize()
            return ' '.join([word.capitalize() for word in humanized.split()])
        except Exception as e:
            self.logger.error(f"Error al humanizar el nombre '{name}': {e}")
            raise
