from abc import ABC, abstractmethod

class BaseAIProvider(ABC):

    @abstractmethod
    def generate_script(self,topic:str) -> str:
        """Genera un guion a partir de un topic."""
        raise NotImplementedError
