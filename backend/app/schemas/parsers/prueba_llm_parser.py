from backend.app.schemas.parsers.llm_parser import LlmResponse
json_valido = """
{
  "narrative": "El niño ayudó a su hermano a hacer sus tareas escolares.",
  "detected_actions": [
    {
      "type": "USER_HELPED",
      "target": "su hermano"
    }
  ]
}
"""

json_invalido = """
{
  "narrative": "texto",
  "detected_actions": [
    {
      "type": "USER_JUMPED",
      "target": "Juan"
    }
  ]
}
"""
try:
    result = LlmResponse.model_validate_json(json_invalido)
    print("ACEPTADO", result)
except Exception as e:
    print("Error", e)
