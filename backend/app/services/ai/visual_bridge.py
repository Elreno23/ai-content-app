
class VisualBridge:
   
    def process_visuals(self, visualMetadata: dict) -> str:
        format = ""
        if visualMetadata:
            format += ", ".join(str(v).strip() for v in visualMetadata.values() if v is not None)
        return format


            
