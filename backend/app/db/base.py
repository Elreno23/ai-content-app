from sqlalchemy.orm import declarative_base

#Base declarativa para definir modelos
Base = declarative_base()

#Importa los modelos:

from app.models.narrative import Narrative
from app.models.detected_action import DetectedAction