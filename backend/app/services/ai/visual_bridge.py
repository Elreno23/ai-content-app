from pathlib import Path
import json
import copy
import httpx

class ComfyUIBridge:
    def __init__(self, workflow_path: Path = "app/services/comfy/workflows/prueba_1.json",base_url: str = "http://127.0.0.1:8188/prompt") -> None:
        self.base_url=base_url.rstrip("/") #PRUEBAS
        with open(workflow_path, "r", encoding="utf-8") as file:
            self.workflow_template : dict = json.load(file)

    def _process_visuals(self, visualMetadata: dict) -> str:
            format = ""
            if visualMetadata:
                format += ", ".join(str(v).strip() for v in visualMetadata.values() if v is not None)
            print(f"ESTA FORMATENADO EL TEXTO?: {format}")
            return format

    def _build_payload(self, promp_text:str) -> dict:
         workflow = copy.deepcopy(self.workflow_template) #Hacemos copia de todo el workflow
         workflow["77"]["inputs"]["text"] = promp_text
         print("--- PAYLOAD GENERADO PARA COPIAR A POSTMAN ---")
         print(json.dumps({"prompt": workflow}, indent=4))
         print("---------------------------------------------")
         return {"prompt":workflow}

    async def send_prompt_text_encoders(self, prompt_text:dict) -> str:
         prompt = self._process_visuals(prompt_text)
         injected_prompt = self._build_payload(prompt)
         try:
              async with httpx.AsyncClient(timeout=30.0) as client:
                   response = await client.post(self.base_url,
                                                json=injected_prompt,
                                                headers={"Content-Type":"application/json"})
                   if response.status_code != 200:
                        return f"Error Comfy, no obtuvimos respuesta (Status: {response.status_code}: {response.text})"
                   try:
                        data = response.json()
                   except ValueError:
                        return f"Error: la respuesta de Comfy no es json válido"
                   if "message" not in data:
                        return f"Error: Respuesta de Comfy {data}"
                   raw_json = data["message"]["content"]
                   print(f"ESTAMOS RECIBIENDO RESPUESTA? {raw_json}")
                   return raw_json
         except httpx.ConnectError:
              return f"Error: conexión con Comfy, está el servidor levantado?"
         except httpx.ReadTimeout:
              return f"Error: Comfy tardó en responder"
         except httpx.Timeout:
              return f"Error: Comfy tardó en responder"
         except Exception as e:
              return f"Error inesperado con Comfy: {str(e)}"
         