import os
from langchain_neo4j import Neo4jVector, Neo4jGraph
from vectors import embedder, COMMENT_VECTOR_INDEX_NAME, ENTITY_VECTOR_INDEX_NAME, OBSERVATION_EMBEDDING_INDEX_NAME, PROCESS_ELEMENT_EMBEDDING_INDEX_NAME, VECTOR_INDEX_DIM

def create_graph_store():
    graph_db = Neo4jGraph(url=os.getenv("NEO4J_URI"), username=os.getenv("NEO4J_USERNAME"), password=os.getenv("NEO4J_PASSWORD"))
    graph_db.query("CREATE CONSTRAINT commentId IF NOT EXISTS FOR (c:Comment) REQUIRE c.id IS NODE KEY")
    graph_db.query("CREATE CONSTRAINT callId IF NOT EXISTS FOR (c:Call) REQUIRE c.id IS NODE KEY")
    graph_db.query("CREATE CONSTRAINT entityName IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS NODE KEY")
    graph_db.query("CREATE CONSTRAINT customerId IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS NODE KEY")
    graph_db.query("CREATE CONSTRAINT representativeId IF NOT EXISTS FOR (r:Representative) REQUIRE r.id IS NODE KEY")
    graph_db.query("CREATE CONSTRAINT observationId IF NOT EXISTS FOR (o:Observation) REQUIRE o.id IS NODE KEY")
    graph_db.query("CREATE CONSTRAINT processElementId IF NOT EXISTS FOR (p:ProcessElement) REQUIRE p.id IS NODE KEY")
    return graph_db

# We're using multiple vector indexes because we want to query for chunks and entities separately
def create_vector_stores():
    comment_vector_db = Neo4jVector(
        embedder,
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        index_name=COMMENT_VECTOR_INDEX_NAME,
        embedding_dimension=VECTOR_INDEX_DIM,
        node_label="Comment"
    )
    comment_vector_db.create_new_index()
    entity_vector_db = Neo4jVector(
        embedder,
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        index_name=ENTITY_VECTOR_INDEX_NAME,
        embedding_dimension=VECTOR_INDEX_DIM,
        node_label="Entity"
    )
    entity_vector_db.create_new_index()
    observation_vector_db = Neo4jVector(
        embedder,
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        index_name=OBSERVATION_EMBEDDING_INDEX_NAME,
        embedding_dimension=VECTOR_INDEX_DIM,
        node_label="Observation"
    )
    observation_vector_db.create_new_index()
    process_element_vector_db = Neo4jVector(
        embedder,
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        index_name=PROCESS_ELEMENT_EMBEDDING_INDEX_NAME,
        embedding_dimension=VECTOR_INDEX_DIM,
        node_label="ProcessElement"
    )
    process_element_vector_db.create_new_index()
    return comment_vector_db, entity_vector_db, observation_vector_db, process_element_vector_db