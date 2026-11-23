"""Contrato de salida del LLM para el desarrollo de capítulos (CHAPTER_SCHEMA).

Reglas aprobadas: entre 4 y 6 escenas por capítulo, entre 2 y 5 beats por
escena, numeración consecutiva sin huecos, una llamada LLM por capítulo.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

MIN_SCENES = 4
MAX_SCENES = 6
MIN_BEATS_PER_SCENE = 2
MAX_BEATS_PER_SCENE = 5


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BeatStructure(StrictModel):
    number: int = Field(ge=1)
    content: str = Field(min_length=20, max_length=2000)


class SceneStructure(StrictModel):
    number: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=200)
    summary: str = Field(min_length=10, max_length=1000)
    beats: list[BeatStructure] = Field(
        min_length=MIN_BEATS_PER_SCENE, max_length=MAX_BEATS_PER_SCENE
    )

    @model_validator(mode="after")
    def check_beat_numbering(self) -> "SceneStructure":
        for i, beat in enumerate(self.beats, start=1):
            if beat.number != i:
                raise ValueError(
                    f"beats de la escena {self.number}: número {beat.number} "
                    f"en posición {i} (se esperaba {i}, numeración consecutiva)"
                )
        return self


class ChapterStructure(StrictModel):
    title: str | None = Field(default=None, max_length=200)
    summary: str = Field(min_length=20, max_length=2000)
    scenes: list[SceneStructure] = Field(
        min_length=MIN_SCENES, max_length=MAX_SCENES
    )

    @model_validator(mode="after")
    def check_scene_numbering(self) -> "ChapterStructure":
        for i, scene in enumerate(self.scenes, start=1):
            if scene.number != i:
                raise ValueError(
                    f"escenas: número {scene.number} en posición {i} "
                    f"(se esperaba {i}, numeración consecutiva)"
                )
        return self


class ChapterOutput(StrictModel):
    """Envoltorio que el LLM debe devolver: {"chapter": {...}}."""

    chapter: ChapterStructure
