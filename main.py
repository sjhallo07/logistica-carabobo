import streamlit as st
from core.graph import build_graph

st.set_page_config(page_title="Logística & Cupones Carabobo (2026)", page_icon="🚗")
st.title("Logística & Cupones Carabobo (2026)")

if "state" not in st.session_state:
    st.session_state["state"] = {"messages": [], "coupon_context": None, "tool_outputs": {}}

user_input = st.text_input("¿En qué podemos ayudarte hoy?", placeholder="Ej: ¿Hay tráfico en la ARC?", key="user_input")

if st.button("Enviar") and user_input:
    # Aquí deberías obtener el embedding de la consulta del usuario (mock para demo)
    query_embedding = [0.01] * 1536
    import streamlit as st
    from core.graph import build_graph
    from core.mcp_bridge import RemoteMCPBridge

    st.set_page_config(page_title="Logística & Cupones Carabobo (2026)", page_icon="🚗")
    st.title("Logística & Cupones Carabobo (2026)")

    bridge = RemoteMCPBridge()

    if "state" not in st.session_state:
        st.session_state["state"] = {"messages": [], "coupon_context": None, "tool_outputs": {}}

    st.header("Consulta rápida")
    user_input = st.text_input("¿En qué podemos ayudarte hoy?", placeholder="Ej: ¿Hay tráfico en la ARC?")

    if st.button("Enviar") and user_input:
        query_embedding = [0.01] * 1536
        graph = build_graph()
        compiled_graph = graph.compile()
        state = st.session_state["state"]
        state["query_embedding"] = query_embedding
        state = compiled_graph.invoke(state)
        st.write(state["messages"][-1] if state.get("messages") else "Sin respuesta.")

    st.markdown("---")
    st.header("Buscar cupones (MCP)")
    search_type = st.selectbox("Tipo de búsqueda", ["profile", "hashtag"])
    limit = st.slider("Límite de resultados", 1, 50, 10)

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
    st.header("Verificar cupón (MCP)")
    coupon_code = st.text_input("Código de cupón a verificar", placeholder="FIRST2026", key="coupon_code")
    if st.button("Verificar cupón", key="verify_coupon_btn") and coupon_code:
        try:
            res = bridge.verify_logistics_coupon(coupon_code)
            st.json(res)
        except Exception as e:
            st.error(f"Error: {e}")
