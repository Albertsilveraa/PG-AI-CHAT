import streamlit as st
from backend import (
    update_credentials, initialize_database, get_tables_and_schema,
    get_sql_query_from_natural_language, execute_sql_query,
    create_df_from_sql, python_shell  
)

# Sidebar para ingresar credenciales
with st.sidebar:
    st.header("Credenciales de conexión")
    input_openai_api_key = st.text_input("OPENAI API KEY", type="password")
    input_db_name = st.text_input("Data Base Name", type="password")
    input_db_user = st.text_input("Data Base User", type="password")
    input_db_password = st.text_input("Data Base Password", type="password")
    input_db_host = st.text_input("Data Base Host", value="localhost")
    input_db_port = st.text_input("Data Base Port", value="5432")

# Verificar si faltan datos de credenciales
if not all([input_openai_api_key, input_db_name, input_db_user, input_db_password, input_db_host, input_db_port]):
    st.sidebar.warning("Por favor, completa todos los campos de credenciales.", icon="⚠")
else:
    # Actualizar las credenciales si se proporcionan todos los datos
    update_credentials(
        api_key=input_openai_api_key,
        db_name=input_db_name,
        db_user=input_db_user,
        db_password=input_db_password,
        db_host=input_db_host,
        db_port=input_db_port
    )

    # Inicializar base de datos y obtener esquema solo si hay credenciales válidas
    initialize_database()
    schema = get_tables_and_schema()

    st.title("POSTGRES-CHAT 🤖🦜🔗")

    # Verificar o establecer modelo en sesión
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Guardar DataFrame en sesión (si generamos uno)
    if "last_df" not in st.session_state:
        st.session_state.last_df = None

    # Mostrar historial de conversación
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Entrada de usuario
    if prompt := st.chat_input("Hazme una pregunta sobre la base de datos :"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generar respuesta de SQLBOT (consulta SQL o PL/pgSQL)
        answer = get_sql_query_from_natural_language(prompt, schema)

        # Mostrar la consulta o respuesta generada
        with st.chat_message("assistant"):
            st.markdown(f"**SQLBOT generó:**\n```\n{answer}\n```")

        # Detectar si la respuesta contiene posibles sentencias SQL
        # (puedes ajustar la detección según tus necesidades)
        sql_keywords = (
            "SELECT", "INSERT", "UPDATE", "DELETE", 
            "CREATE", "DROP", "BEGIN", "END", 
            "DECLARE", "PROCEDURE", "FUNCTION", "CALL"
        )
        if any(keyword in answer.upper() for keyword in sql_keywords):
            results = execute_sql_query(answer)  # intentalo con la lógica normal

            # Si es un SELECT y no hubo error (lista de tuplas),
            # podemos convertirlo en DF para mostrarlo más limpio.
            # Para eso, repetimos la consulta con create_df_from_sql.
            if "select" in answer.lower() and isinstance(results, list):
                # Volvemos a traer el resultado pero esta vez en forma de DataFrame
                try:
                    df = create_df_from_sql(answer)
                    st.session_state.last_df = df  # guardarlo en session_state
                    st.markdown("**Resultados en forma de DataFrame:**")
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Error al crear DataFrame: {e}")

            else:
                # Para otro tipo de query, results será mensaje de éxito o lista
                st.markdown("**Resultados de la consulta:**")
                if isinstance(results, str):
                    st.write(results)
                else:
                    # Mostrar fila por fila
                    if results:
                        for row in results:
                            st.write(row)
                    else:
                        st.write("Consulta ejecutada. (Sin resultados o tabla vacía).")
        else:
            # Si no parece ser SQL, lo mostramos tal cual
            st.markdown(answer)

        # Guardar la respuesta en el historial
        st.session_state.messages.append({"role": "assistant", "content": answer})

    st.divider()
    #st.subheader("Ejecutar código Python sobre el último DataFrame (opcional)")
    #st.markdown("""
   # Si tu última consulta generó un DataFrame, puedes escribir código Python aquí para analizarlo
    #usando la variable `df`.
    #""")

    # Campo de texto para código Python
   # python_code = st.text_area("Código Python:")

    #if st.button("Ejecutar código Python"):
     #   if st.session_state.last_df is None:
      #      st.warning("No hay ningún DataFrame disponible todavía.")
       # else:
        #    df = st.session_state.last_df
         #   # Llamamos a python_shell, pasándole el DF en context_vars
          #  output = python_shell(python_code, context_vars={"df": df})
           # st.markdown("**Salida de la ejecución Python:**")
            #st.write(output)
