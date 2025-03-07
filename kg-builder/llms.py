from langchain_openai import ChatOpenAI
from structured_outputs import EntityArray, StateObservation, ActionSelection, DecisionInference, GroupDescription, ResolutionInference

# LLM enums
FAST_CHAT = "gpt-4o-mini"
CHAT = "gpt-4o"

entity_extractor_llm = ChatOpenAI(model=FAST_CHAT, temperature=0).with_structured_output(EntityArray)
group_description_llm = ChatOpenAI(model=FAST_CHAT, temperature=0).with_structured_output(GroupDescription)

state_observation_llm = ChatOpenAI(model=FAST_CHAT, temperature=0.5).with_structured_output(StateObservation)
action_selection_llm = ChatOpenAI(model=FAST_CHAT, temperature=0.5).with_structured_output(ActionSelection)
decision_inference_llm = ChatOpenAI(model=FAST_CHAT, temperature=0.3).with_structured_output(DecisionInference)
resolution_inference_llm = ChatOpenAI(model=FAST_CHAT, temperature=0.5).with_structured_output(ResolutionInference)