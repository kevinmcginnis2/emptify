from typing import Literal

from pydantic import BaseModel

VoiceMode = Literal["client", "internal"]


class VoiceTrait(BaseModel):
    label: str
    value: str


class VoiceProfileDoc(BaseModel):
    exec_user_id: str
    mode: VoiceMode
    sample_size: str
    rebuilding: bool = False
    notes: str = ""
    traits: list[VoiceTrait] = []
