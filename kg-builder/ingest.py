from dotenv import load_dotenv
load_dotenv()

import os
from stores import create_graph_store, create_vector_stores
from transcript_processing_agent import transcript_processing_agent

graph_db = create_graph_store()
comment_vector_db, entity_vector_db, observation_vector_db, process_element_vector_db = create_vector_stores()
# check env variable indicating dev mode
if os.getenv("DEV"):
    print("DEV MODE")
    graph_db.query("MATCH (n) DETACH DELETE n")

file_uri = "https://storage.googleapis.com/neo4j-se-jeff-davis/callcenter/transcripts.json"

transcript_processing_agent(file_uri, graph_db).invoke({"comments": []})