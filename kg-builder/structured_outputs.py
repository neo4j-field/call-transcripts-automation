from pydantic import BaseModel, Field
from typing import List

class Entity(BaseModel):
    name: str = Field(None, title="The name of the entity")
    description: str = Field(None, title="A 1-2 sentence description of the entity")
    quote: str = Field(None, title="An exactly-copied quote snippet from the chunk that mentions the entity")

class EntityArray(BaseModel):
    entities: List[Entity] = Field(None, title="An array of extracted entities")

class StateObservation(BaseModel):
    state: str = Field(None, title="A description of the current state of the conversation")

class ActionSelection(BaseModel):
    action: str = Field(None, title="A description of the action taken based on the most recent comment")

class DecisionInference(BaseModel):
    decision: str = Field(None, title="A description of the decision made based on the most recent comment")

class ResolutionInference(BaseModel):
    resolution: str = Field(None, title="A description of the resolution made based on the call")

class GroupDescription(BaseModel):
    name: str = Field(None, title="The name of the group")
    description: str = Field(None, title="A 1-paragraph description of the group's characteristic ideas")