import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from core.database import match_documents
from core.graph import build_graph

class TestCuponesComidaValencia(unittest.TestCase):
    def test_buscar_cupones_comida_valencia(self):
        # Simula un embedding para la consulta "cupones de descuento en comidas valencia"
        query_embedding = [0.01] * 1536
        resultados = match_documents(query_embedding)
        # Esperamos que retorne una lista o un objeto con atributo 'data'
        self.assertTrue(isinstance(resultados, list) or hasattr(resultados, 'data'))
        # Si hay resultados, al menos uno debe estar relacionado con comida y valencia
        if isinstance(resultados, list) and resultados:
            hay_comida_valencia = any(
                ("comida" in str(r).lower() or "food" in str(r).lower()) and "valencia" in str(r).lower()
                for r in resultados
            )
            self.assertTrue(hay_comida_valencia)

class TestCuponesComidaValenciaGraph(unittest.TestCase):
    def test_respuesta_simulada_cupones_comida_valencia(self):
        # Estado simulado con contexto de cupón relevante
        state = {
            "query_embedding": [0.01] * 1536,
            "messages": [],
            "coupon_context": [
                {
                    "restaurante": "Arepas Valencia",
                    "descuento": "20% en tu primera compra",
                    "codigo": "FIRST2026",
                    "vigencia": "2026-04-30"
                }
            ],
            "tool_outputs": {}
        }
        graph = build_graph()
        compiled = graph.compile()
        result = compiled.invoke(state)
        self.assertIn("messages", result)
        self.assertTrue(any("Arepas Valencia" in m or "FIRST2026" in m for m in result["messages"]))

if __name__ == "__main__":
    unittest.main()
