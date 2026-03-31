import streamlit as st
from core.graph import build_graph
from core.mcp_bridge import RemoteMCPBridge
from core.database import save_instagram_coupons
import re
import os

st.set_page_config(page_title="Logística & Cupones Carabobo (2026)", page_icon="🚗")
st.title("Logística & Cupones Carabobo (2026)")

bridge = RemoteMCPBridge()

if "state" not in st.session_state:
    st.session_state["state"] = {"messages": [], "coupon_context": None, "tool_outputs": {}}

# --- Consulta rápida (Chatbot) ---
st.header("Consulta rápida — Chatbot")

# simple chat history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = [
        {"role": "system", "content": "Logística & Cupones Carabobo (2026) — Asistente de consultas rápidas."}
    ]

def detect_coupon_intent(text: str):
    t = text.lower()
    keywords = ["cupon", "cupón", "descuento", "promo", "promoción", "promocion", "codigo", "código"]
    if not any(k in t for k in keywords):
        return None
    # look for known segment names
    segs = [s.lower() for s in RemoteMCPBridge.ALLOWED_SEGMENTS]
    for s in segs:
        if s in t:
            return ("segment", s)
    # hashtag pattern
    m = re.search(r"#([A-Za-z0-9_\-]+)", text)
    if m:
        return ("hashtag", m.group(1))
    # 'en <place>' fallback
    m2 = re.search(r"en\s+([A-Za-z0-9áéíóúñÑ\-]+)", text.lower())
    if m2:
        return ("hashtag", m2.group(1))
    return ("search", text)

def render_chat():
    for msg in st.session_state["chat_history"]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if hasattr(st, "chat_message"):
            with st.chat_message(role):
                st.write(content)
        else:
            if role == "assistant":
                st.markdown(f"**Asistente:** {content}")
            elif role == "user":
                st.markdown(f"**Tú:** {content}")
            else:
                st.markdown(f"**{role}:** {content}")

render_chat()

# input
if hasattr(st, "chat_input"):
    user_msg = st.chat_input("¿En qué podemos ayudarte hoy?")
else:
    user_msg = st.text_input("¿En qué podemos ayudarte hoy?", placeholder="Ej: Buscar cupones en San Diego", key="chat_input_text")

if user_msg:
    st.session_state["chat_history"].append({"role": "user", "content": user_msg})
    intent = detect_coupon_intent(user_msg)
    with st.spinner("Procesando..."):
        try:
            bridge = RemoteMCPBridge()
            assistant_msg = None
            if intent and intent[0] in ("segment", "hashtag", "search"):
                kind, value = intent
                # normalize value
                if kind == "segment":
                    query = value
                else:
                    query = value
                # use MCP bridge to search hashtags
                res = bridge.search_instagram_hashtag(query, limit=25)
                results = res.get("results", []) if isinstance(res, dict) else []
                if results:
                    save_res = save_instagram_coupons(results, source="chat_search", source_id=query)
                    assistant_msg = f"Encontré {len(results)} posts con códigos para '{query}'. Guardados en la base de datos (status: {save_res.get('status', save_res)}). Ejemplos: {', '.join([', '.join(r.get('codes',[])) for r in results[:3]])}"
                else:
                    assistant_msg = f"No se encontraron códigos para '{query}'."
            else:
                # fallback to graph processing
                query_embedding = [0.01] * 1536
                graph = build_graph()
                compiled_graph = graph.compile()
                state = st.session_state.get("state", {})
                state["query_embedding"] = query_embedding
                state.setdefault("messages", []).append(f"User query: {user_msg}")
                result_state = compiled_graph.invoke(state)
                if result_state.get("messages"):
                    assistant_msg = result_state["messages"][-1]
                else:
                    assistant_msg = "Lo siento, no pude generar una respuesta."

            st.session_state["chat_history"].append({"role": "assistant", "content": assistant_msg})
            # re-render chat
            render_chat()
            if "chat_input_text" in st.session_state:
                st.session_state["chat_input_text"] = ""
        except Exception as e:
            err = f"Error al procesar la consulta: {e}"
            st.session_state["chat_history"].append({"role": "assistant", "content": err})
            render_chat()

st.markdown("---")

# --- Buscar cupones (MCP) ---
st.header("Buscar cupones (MCP)")
search_type = st.selectbox("Tipo de búsqueda", ["profile", "hashtag"], key="search_type")
limit = st.slider("Límite de resultados", 1, 50, 10, key="limit")

if search_type == "profile":
    profile_url = st.text_input("URL del perfil (público)", placeholder="https://www.instagram.com/usuario/", key="profile_url")
    if st.button("Buscar cupones en perfil", key="search_profile_btn") and profile_url:
        with st.spinner("Buscando posts y extrayendo códigos..."):
            try:
                res = bridge.search_instagram_profile(profile_url, limit=limit)
                st.success("Búsqueda completada")
                results = res.get("results", []) if isinstance(res, dict) else []
                if results:
                    st.dataframe(results)
                    if st.button("Guardar resultados en Supabase", key="save_profile_btn"):
                        from core.database import save_instagram_coupons
                        save_res = save_instagram_coupons(results, source="profile", source_id=profile_url)
                        st.write(save_res)
                else:
                    st.info("No se encontraron códigos en los posts.")
            except Exception as e:
                st.error(f"Error: {e}")

else:
    hashtag = st.text_input("Hashtag (sin #)", placeholder="promociones", key="hashtag")
    if st.button("Buscar cupones por hashtag", key="search_hashtag_btn") and hashtag:
        with st.spinner("Buscando por hashtag..."):
            try:
                res = bridge.search_instagram_hashtag(hashtag, limit=limit)
                st.success("Búsqueda completada")
                results = res.get("results", []) if isinstance(res, dict) else []
                if results:
                    st.dataframe(results)
                    if st.button("Guardar resultados en Supabase", key="save_hashtag_btn"):
                        from core.database import save_instagram_coupons
                        save_res = save_instagram_coupons(results, source="hashtag", source_id=hashtag)
                        st.write(save_res)
                else:
                    st.info("No se encontraron códigos con ese hashtag.")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")

# --- Verificar cupón ---
st.header("Verificar cupón (MCP)")
coupon_code = st.text_input("Código de cupón a verificar", placeholder="FIRST2026", key="coupon_code")
if st.button("Verificar cupón", key="verify_coupon_btn") and coupon_code:
    try:
        res = bridge.verify_logistics_coupon(coupon_code)
        st.json(res)
    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")

# --- Agregar cupón manualmente (MCP) ---
st.header("Agregar cupón (MCP)")
with st.form(key='add_coupon_form'):
    c_code = st.text_input("Código", placeholder="EJEMPLO123")
    c_place = st.text_input("Lugar / Ciudad", value="Valencia")
    c_business = st.text_input("Negocio / Comercio", placeholder="Nombre del negocio")
    c_address = st.text_input("Dirección", placeholder="Av. Bolivar 123")
    c_exp = st.date_input("Fecha de expiración (opcional)")
    submitted = st.form_submit_button("Agregar cupón")
    if submitted:
        try:
            payload = {
                "code": c_code,
                "place": c_place,
                "business": c_business,
                "address": c_address,
                "expiration": c_exp.isoformat() if hasattr(c_exp, 'isoformat') else str(c_exp),
                "source": "manual_ui"
            }
            resp = bridge.add_coupon(payload)
            st.success(f"Cupón agregado: {resp}")
        except Exception as e:
            st.error(f"Error agregando cupón: {e}")
