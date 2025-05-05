import json
import os

import streamlit as st
import llm_parsing as lp
import to_iacp as ti
import compare_json as cjson
from config import LLM_Settings

st.set_page_config(layout="wide")
st.title("Обработка анамнеза жизни")

if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'processing_results' not in st.session_state:
    st.session_state.processing_results = {
        'llm1': "",
        'llm2': "",
        'anamnez': "",
        'result_json_1': "",
        'result_json_2': ""
    }

uploaded_file = st.file_uploader(
    "Выберите файл для обработки",
    label_visibility="visible",
    key="file_uploader"
)

placeholder = st.empty()

def process_file(uploaded_file):
    file_name = uploaded_file.name
    file_base_name = os.path.splitext(file_name)[0]

    placeholder.progress(0, "Файл в обработке...")
    bytes_data = uploaded_file.read()
    placeholder.progress(50, "Файл в обработке...")

    llm1, llm2, anamnez = lp.parsing_anamnez(bytes_data.decode("utf-8"))

    llm1 = llm1.replace("```json", "").replace("```", "")
    result_json_1 = ti.main(llm1, file_base_name)
    placeholder.progress(70, "Файл в обработке...")
    result_json_2 = ti.main(llm2, file_base_name)
    placeholder.progress(90, "Файл в обработке...")
    st.session_state.processing_results = {
        'llm1': llm1,
        'llm2': llm2,
        'anamnez': anamnez,
        'result_json_1': result_json_1,
        'result_json_2': result_json_2
    }

    st.session_state.uploaded_file = uploaded_file

def clear_state():
    st.session_state.uploaded_file = None
    st.session_state.processing_results = {
        'llm1': "",
        'llm2': "",
        'anamnez': "",
        'result_json_1': "",
        'result_json_2': ""
    }


if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
    process_file(uploaded_file)

if st.session_state.uploaded_file is not None:
    st.button("Очистить и загрузить новый файл", on_click=clear_state)

results = st.session_state.processing_results

col1, col2 = st.columns([2, 2], gap="medium")
if results['result_json_1'] != "" or results['result_json_2'] != "":
    with col1:
        st.header(LLM_Settings.LLM1_NAME, divider=True)

    with col2:
        st.header(LLM_Settings.LLM2_NAME, divider=True)

    col1, col2 = st.columns([2, 2], gap="medium", border=True)

    with col1:
        st.subheader("JSON 1")
        st.json(results['result_json_1'], expanded=False)


    with col2:
        st.subheader("JSON 2")
        st.json(results['result_json_2'], expanded=False)

    with st.expander("Сравнение JSON", expanded=False):
        if 'compare_json' not in st.session_state:
            st.session_state.compare_json = cjson.compare_json(results['result_json_1'], results['result_json_2'])
        st.markdown(st.session_state.compare_json.replace("```markdown", "").replace("```", ""), unsafe_allow_html=True)
        placeholder.progress(100, "Файл в обработке...")
        placeholder.markdown(st.session_state.processing_results['anamnez'])

    col3, col4 = st.columns([2, 2], gap="medium")

    with col3:
        st.download_button(
            label="Download json 1",
            data=json.dumps(results['result_json_1'], ensure_ascii=False, indent=2),
            file_name="result_llm1.json",
            mime="application/json",
            key="download_llm1"
        )

    with col4:
        st.download_button(
            label="Download json 2",
            data=json.dumps(results['result_json_2'], ensure_ascii=False, indent=2),
            file_name="result_llm2.json",
            mime="application/json",
            key="download_llm2"
        )