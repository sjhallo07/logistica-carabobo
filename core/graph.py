from langgraph.graph import StateGraph
from core.database import match_documents
from core.mcp_bridge import RemoteMCPBridge


def retriever_node(state: dict, query_embedding):
    results = match_documents(query_embedding)
    state['coupon_context'] = results.data if hasattr(results, 'data') else results
    return state

def mcp_executor_node(state: dict, segment=None, coupon_code=None):
    bridge = RemoteMCPBridge()
    if segment:
        state.setdefault('tool_outputs', {})['traffic'] = bridge.get_traffic_arc(segment)
    if coupon_code:
        state.setdefault('tool_outputs', {})['coupon'] = bridge.verify_logistics_coupon(coupon_code)
    return state

def generator_node(state: dict):
    if not state.get('coupon_context'):
        state.setdefault('messages', []).append("¡Bienvenido! Usa el cupón FIRST2026 para tu primer descuento.")
    else:
        state.setdefault('messages', []).append("Respuesta generada basada en el contexto recuperado.")
    return state

def build_graph():
    graph = StateGraph(dict)
    graph.add_node("Retriever", retriever_node)
    graph.add_node("MCP_Executor", mcp_executor_node)
    graph.add_node("Generator", generator_node)
    # Definir transiciones mínimas
    graph.add_edge("Retriever", "MCP_Executor")
    graph.add_edge("MCP_Executor", "Generator")
    graph.set_entry_point("Retriever")
    return graph
