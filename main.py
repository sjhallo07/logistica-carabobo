import streamlit as st
from core.graph import build_graph

st.set_page_config(page_title="Logística & Cupones Carabobo (2026)", page_icon="🚗")
st.title("Logística & Cupones Carabobo (2026)")

if "state" not in st.session_state:
    st.session_state["state"] = {"messages": [], "coupon_context": None, "tool_outputs": {}}

user_input = st.text_input("¿En qué podemos ayudarte hoy?", placeholder="Ej: ¿Hay tráfico en la ARC?")

if st.button("Enviar") and user_input:
    # Aquí deberías obtener el embedding de la consulta del usuario (mock para demo)
    query_embedding = [0.01] * 1536
    graph = build_graph()
    compiled_graph = graph.compile()
    state = st.session_state["state"]
    state = compiled_graph.invoke(state, query_embedding=query_embedding)
    st.write(state.messages[-1] if state.messages else "Sin respuesta.")
