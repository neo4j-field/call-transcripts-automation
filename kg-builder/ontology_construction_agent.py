from functions import read_nodes, write_entities, project_process_observations_to_gds, process_community_detection, write_process_communities, close_gds_session, write_lifted_rels, infer_names_for_process_elements
from langgraph.graph import StateGraph, START, END
from typing import List, NotRequired
from typing_extensions import TypedDict
from parallel import MAX_PROCESSES
from graphdatascience import GraphDataScience as GDS
from graphdatascience.session.aura_graph_data_science import AuraGraphDataScience as AuraGDS
from graphdatascience.graph.graph_object import Graph as GDSGraph

def ontology_construction_agent(graph_db, gds, session_name):
    class Document(TypedDict):
        id: str
        description: str

    class Entity(TypedDict):
        id: str
        name: str
        description: str

    class State(TypedDict):
        documents: List[Document]
        entities: List[Entity]
        gds_graph: GDSGraph | None

    def get_documents(state):
        print("Getting documents from Neo4j...")
        documents = read_nodes(graph_db, label="Comment|Observation|ProcessElement")
        return {"documents": documents}

    def seed_entity_index(state):
        print("Seeding entity index...")
        documents = state["documents"]
        write_entities([documents[0]], graph_db, label="Comment|Observation|ProcessElement", seed=True)
        return {}
    
    def merge_entities_for_docs_batch(i):
        def fn(state):
            print(f"Merging entities for docs batch {i}")
            # Did seeding already
            num_docs = len(state["documents"]) - 1
            docs = state["documents"][1:][i * num_docs // MAX_PROCESSES:(i + 1) * num_docs // MAX_PROCESSES]
            # print(docs)
            write_entities(docs, graph_db, label="Comment|Observation|ProcessElement")
            return {}
        return fn

    def get_entities(state):
        print("Getting entities from Neo4j...")
        # entities = read_entities(graph_db)
        entities = read_nodes(graph_db, label="Entity")
        return {"entities": entities}

    # def embed_extracted_entities(state):
    #     print("Embedding entities...")
    #     entities = state["entities"]
    #     embed_entities(entities, graph_db)
    #     return {}

    # def project_gds_graph(state):
    #     print("Projecting GDS graph...")
    #     G = project_process_observations_to_gds(gds, session_name)
    #     return {"gds_graph": G}

    # def discover_canonical_process_elements(state):
    #     print("Discovering canonical process elements...")
    #     process_community_detection(gds, state["gds_graph"])
    #     write_process_communities(graph_db)
    #     return {}

    # def close_process_gds_session(state):
    #     print("Closing GDS session...")
    #     close_gds_session(gds, state["gds_graph"])
    #     return {"gds_graph": None}

    # def lift_up_relationships(state):
    #     print("Creating lifted relationships...")
    #     write_lifted_rels(graph_db)
    #     return {}

    # def get_canonical_process_elements(state):
    #     print("Getting process elements from Neo4j...")
    #     process_elements = read_process_elements(graph_db)
    #     return {"process_elements": process_elements}

    # def name_canonical_process_elements_batch(i):
    #     def fn(state):
    #         print(f"Naming canonical process elements for batch {i}...")
    #         num_process_elements = len(state["process_elements"])
    #         process_elements = state["process_elements"][i * num_process_elements // MAX_PROCESSES:(i + 1) * num_process_elements // MAX_PROCESSES]
    #         infer_names_for_process_elements([pe["id"] for pe in process_elements], graph_db)
    #         return {}
    #     return fn

    agent_graph = StateGraph(State)

    agent_graph.add_node("get_documents", get_documents)
    agent_graph.add_edge(START, "get_documents")
    # agent_graph.add_node("get_process_observations", get_process_observations)
    # agent_graph.add_edge(START, "get_process_observations")
    # merging process observations
    # for j in range(MAX_PROCESSES):
    #     agent_graph.add_node(f"Merge process observations {j}", merge_process_observations_batch(j))
    #     agent_graph.add_edge("get_calls", f"Merge process observations {j}")
    #     agent_graph.add_edge(f"Merge process observations {j}", "get_process_observations")

    agent_graph.add_node("seed_entity_index", seed_entity_index)
    agent_graph.add_node("get_entities", get_entities)
    agent_graph.add_edge("get_documents", "seed_entity_index")
    # agent_graph.add_edge("get_process_observations", "map_transitions")

    # merging extracted entities from process observations
    for j in range(MAX_PROCESSES):
        agent_graph.add_node(f"Merge entities for docs batch {j}", merge_entities_for_docs_batch(j))
        agent_graph.add_edge("seed_entity_index", f"Merge entities for docs batch {j}")
        agent_graph.add_edge(f"Merge entities for docs batch {j}", END)

    # agent_graph.add_node("embed_extracted_entities", embed_extracted_entities)
    # agent_graph.add_edge("get_entities", END)
    # agent_graph.add_edge("embed_extracted_entities", END)

    # agent_graph.add_node("project_gds_graph", project_gds_graph)
    # # agent_graph.add_edge(START, "project_gds_graph")
    # agent_graph.add_edge("embed_process_observations", "project_gds_graph")
    # agent_graph.add_edge("map_transitions", "project_gds_graph")
    # agent_graph.add_node("discover_canonical_process_elements", discover_canonical_process_elements)
    # agent_graph.add_edge("project_gds_graph", "discover_canonical_process_elements")
    # agent_graph.add_node("close_process_gds_session", close_process_gds_session)
    # agent_graph.add_edge("discover_canonical_process_elements", "close_process_gds_session")
    # agent_graph.add_edge("close_process_gds_session", END)
    # agent_graph.add_node("lift_up_relationships", lift_up_relationships)
    # agent_graph.add_edge("discover_canonical_process_elements", "lift_up_relationships")
    # # agent_graph.add_node("name_canonical_process_elements", name_canonical_process_elements)
    # # agent_graph.add_edge("lift_up_relationships", "name_canonical_process_elements")
    # # agent_graph.add_edge("name_canonical_process_elements", END)
    # agent_graph.add_node("get_canonical_process_elements", get_canonical_process_elements)
    # agent_graph.add_edge("lift_up_relationships", "get_canonical_process_elements")
    # # agent_graph.add_edge("name_canonical_process_elements", "get_canonical_process_elements")

    # for j in range(MAX_PROCESSES):
    #     agent_graph.add_node(f"Name canonical process elements {j}", name_canonical_process_elements_batch(j))
    #     agent_graph.add_edge("get_canonical_process_elements", f"Name canonical process elements {j}")
    #     agent_graph.add_edge(f"Name canonical process elements {j}", END)

    agent = agent_graph.compile()
    return agent