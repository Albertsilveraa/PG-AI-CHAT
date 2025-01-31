import streamlit as st
import pandas as pd
from describe import *
#from interpretation *

from backend5 import SQLBot  # Asegúrate de que backend_modular.py está en el mismo directorio
import json

# Configuración de la página
st.set_page_config(
    page_title="MySQL-Chat Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .sql-code {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 10px;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
    }
    .stButton>button {
        width: 100%;
    }
    .stTextInput>div>div>input {
        /* Puedes agregar estilos personalizados aquí */
    }
</style>
""", unsafe_allow_html=True)

# Inicialización del bot con manejo de errores
@st.cache_resource
def get_bot():
    try:
        bot = SQLBot()
        return bot
    except Exception as e:
        st.error(f"Error al inicializar el bot: {str(e)}")
        return None

# Inicializar el bot
bot = get_bot()

# Sidebar para configuración
with st.sidebar:
    st.header("📊 Configuración de la Base de Datos")
    
    # Formulario de credenciales
    with st.form("credentials_form"):
        input_openai_api_key = st.text_input("OpenAI API Key", type="password")
        input_db_name = st.text_input("Nombre de la Base de Datos")
        input_db_user = st.text_input("Usuario")
        input_db_password = st.text_input("Contraseña", type="password")
        input_db_host = st.text_input("Host", value="localhost")
        input_db_port = st.text_input("Puerto", value="3306")
        
        submit_button = st.form_submit_button("Actualizar Credenciales")
        
        if submit_button and bot:
            try:
                bot.update_credentials(
                    api_key=input_openai_api_key if input_openai_api_key else None,
                    db_name=input_db_name if input_db_name else None,
                    db_user=input_db_user if input_db_user else None,
                    db_password=input_db_password if input_db_password else None,
                    db_host=input_db_host if input_db_host else None,
                    db_port=input_db_port if input_db_port else None
                )
                st.success("¡Credenciales actualizadas correctamente!")
                
                # Mostrar el esquema de la base de datos
                try:
                    schema = bot.get_schema()
                    if schema:
                        st.success("Conexión a la base de datos establecida")
                        with st.expander("Ver esquema de la base de datos"):
                            st.code(schema)
                except Exception as e:
                    st.error(f"Error al obtener el esquema: {str(e)}")
            except Exception as e:
                st.error(f"Error al actualizar credenciales: {str(e)}")

# Título principal
st.title("🤖 MySQL-Chat Bot")
st.markdown("### Tu asistente inteligente para consultas de base de datos")

# Inicializar estado de la sesión
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial de mensajes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], dict):
            # Si el contenido es un diccionario (para resultados de consultas)
            if "sql_query" in message["content"]:
                st.code(message["content"]["sql_query"], language="sql")
            if "data" in message["content"] and isinstance(message["content"]["data"], pd.DataFrame) and not message["content"]["data"].empty:
                st.dataframe(message["content"]["data"])
            if "message" in message["content"]:
                st.write(message["content"]["message"])
        else:
            # Si es un mensaje simple
            st.markdown(message["content"])

# Input del usuario
if prompt := st.chat_input("Hazme una pregunta sobre la base de datos..."):
    # Validar que el bot esté inicializado
    if not bot:
        st.error("El bot no está inicializado correctamente. Por favor, verifica las credenciales.")
        st.stop()

    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesar la consulta paso a paso
    try:
        with st.spinner("Interpretando tu consulta..."):
            # Paso 1: Interpretación
            query_structure = bot.interpret_user_query(prompt)
            st.write("**Estructura de la consulta interpretada:**", query_structure)

        with st.spinner("Generando consulta SQL..."):
            # Paso 2: Generar SQL
            sql_query = bot.generate_sql(query_structure)
            st.code(sql_query, language="sql")

        with st.spinner("Ejecutando consulta..."):
            # Paso 3: Ejecutar consulta
            response = bot.execute_query(sql_query)

            # Mostrar resultados
            with st.chat_message("assistant"):
                if response["success"]:
                    response_content = {}
                    
                    if "sql_query" in response:
                        response_content["sql_query"] = response["sql_query"]
                        st.code(response["sql_query"], language="sql")
                    
                    if "data" in response and isinstance(response["data"], pd.DataFrame) and not response["data"].empty:
                        response_content["data"] = response["data"]
                        st.dataframe(response["data"])
                    
                    if "message" in response:
                        response_content["message"] = response["message"]
                        st.write(response["message"])
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_content
                    })
                else:
                    error_message = f"Error: {response['error']}"
                    st.error(error_message)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message
                    })
    except Exception as e:
        error_message = f"Error inesperado: {str(e)}"
        st.error(error_message)
        st.session_state.messages.append({
            "role": "assistant",
            "content": error_message
        })

# Botones de acción en el sidebar
st.sidebar.markdown("### 🛠️ Herramientas")
if st.sidebar.button("Limpiar Historial"):
    st.session_state.messages = []
    st.experimental_rerun()

# Mostrar el esquema actual
if bot:
    try:
        with st.sidebar.expander("Ver esquema actual"):
            schema = bot.get_schema()
            if schema:
                st.code(schema)
            else:
                st.warning("No hay esquema disponible")
    except Exception as e:
        st.sidebar.error(f"Error al cargar el esquema: {str(e)}")
