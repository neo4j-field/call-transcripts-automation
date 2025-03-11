import os
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
COMMENT_VECTOR_INDEX_NAME = "commentEmbeddings"
ENTITY_VECTOR_INDEX_NAME = "entityEmbeddings"
OBSERVATION_EMBEDDING_INDEX_NAME = "observationEmbeddings"
PROCESS_ELEMENT_EMBEDDING_INDEX_NAME = "processElementEmbeddings"
VECTOR_INDEX_DIM = 128
VECTOR_EQUIVALENCE_THRESHOLD = 0.9
DEFAULT_k = 7

# embedder = OpenAIEmbeddings(model=DEFAULT_EMBEDDING_MODEL, dimensions=VECTOR_INDEX_DIM)

embedder = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model=DEFAULT_EMBEDDING_MODEL,
    openai_api_version="2025-01-01-preview",
    dimensions=VECTOR_INDEX_DIM
)