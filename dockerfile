# Usamos una imagen base de Python 3.12.5
FROM python:3.12.5-slim

# Instalamos dependencias necesarias para compilar psycopg2 (si es necesario)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Establecemos el directorio de trabajo en el contenedor
WORKDIR /app

# Copiamos los archivos necesarios al contenedor
COPY requirements.txt ./

# Instalamos las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código fuente a la imagen
COPY src/ ./src/

# Copiamos el archivo .env (asegurándonos de que las variables de entorno estén en el contenedor)
COPY .env ./

# Exponemos el puerto (si tu aplicación lo usa, por ejemplo, para un servidor web o API)
EXPOSE 8501

# Definimos la variable de entorno (si es necesario)
ENV VAR_NAME=value

# El comando que se ejecutará cuando se inicie el contenedor
CMD ["streamlit", "run","src/app.py"]
