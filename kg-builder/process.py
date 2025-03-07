from dotenv import load_dotenv
load_dotenv()

import os
from stores import create_graph_store, create_vector_stores
from gds import create_graph_data_science_session
from process_discovery_agent import process_discovery_agent

graph_db = create_graph_store()
comment_vector_db, entity_vector_db, observation_vector_db, process_element_vector_db = create_vector_stores()
session_name = "process_discovery_gds_session"
gds = create_graph_data_science_session(session_name)
# check env variable indicating dev mode
if os.getenv("DEV"):
    print("DEV MODE")
    graph_db.query("MATCH (n:Observation|ProcessElement) DETACH DELETE n")

process_discovery_agent(graph_db, gds, session_name).invoke({"calls": []})