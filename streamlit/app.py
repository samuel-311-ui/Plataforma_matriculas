import requests
import streamlit as st


API_URL = "http://api:8000"


st.set_page_config(
    page_title="Matrícula Académica",
    layout="wide"
)


st.title(" Plataforma de Matrícula Académica")

st.write(
    "Sistema para analizar el comportamiento "
    "de una plataforma de matrícula durante periodos de alta demanda."
)

#Mostrar estudiantes

st.header("Estudiantes")

if st.button("Consultar estudiantes"):

    respuesta = requests.get(
        f"{API_URL}/estudiantes"
    )

    if respuesta.status_code == 200:

        st.dataframe(
            respuesta.json()
        )

    else:

        st.error(
            "No se pudieron consultar los estudiantes."
        )

#Crear estudiante

st.header("Registrar estudiante")

nombre = st.text_input(
    "Nombre"
)

correo = st.text_input(
    "Correo"
)


if st.button("Registrar estudiante"):

    datos = {
        "nombre": nombre,
        "correo": correo
    }

    respuesta = requests.post(
        f"{API_URL}/estudiantes",
        json=datos
    )

    if respuesta.status_code == 200:

        st.success(
            "Estudiante registrado correctamente."
        )

    else:

        st.error(
            respuesta.text
        )