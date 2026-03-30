import unittest
from core.database import match_documents
from core.graph import build_graph

class TestDatabase(unittest.TestCase):
    def test_match_documents_returns_list(self):
        # Simula un embedding de consulta
        query_embedding = [0.01] * 1536
        result = match_documents(query_embedding)
        self.assertTrue(isinstance(result, list) or hasattr(result, 'data'))

class TestGraph(unittest.TestCase):
    def test_graph_flow(self):
        graph = build_graph()
        compiled = graph.compile()
        state = {"query_embedding": [0.01]*1536, "messages": [], "coupon_context": None, "tool_outputs": {}}
        result = compiled.invoke(state)
        self.assertIn("messages", result)
        self.assertTrue(len(result["messages"]) > 0)

if __name__ == "__main__":
    unittest.main()
