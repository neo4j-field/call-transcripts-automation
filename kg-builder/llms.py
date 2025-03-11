from langchain_openai import AzureChatOpenAI, ChatOpenAI
from structured_outputs import EntityArray, StateObservation, ActionSelection, GroupDescription, ResolutionInference

# LLM enums
FAST_CHAT = "gpt-4o-mini"
CHAT = "gpt-4o"

entity_extractor_llm = AzureChatOpenAI(azure_deployment=FAST_CHAT, api_version="2025-01-01-preview", temperature=0).with_structured_output(EntityArray)
group_description_llm = AzureChatOpenAI(azure_deployment=FAST_CHAT, api_version="2025-01-01-preview", temperature=0).with_structured_output(GroupDescription)

state_observation_llm = AzureChatOpenAI(azure_deployment=FAST_CHAT, api_version="2025-01-01-preview", temperature=0.5).with_structured_output(StateObservation)
action_selection_llm = AzureChatOpenAI(azure_deployment=FAST_CHAT, api_version="2025-01-01-preview", temperature=0.5).with_structured_output(ActionSelection)
resolution_inference_llm = AzureChatOpenAI(azure_deployment=FAST_CHAT, api_version="2025-01-01-preview", temperature=0.5).with_structured_output(ResolutionInference)