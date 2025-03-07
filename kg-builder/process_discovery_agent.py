from functions import read_nodes, embed_nodes, write_process_observations, write_transition_rels, write_entities, project_process_observations_to_gds, process_community_detection, write_process_communities, close_gds_session, write_lifted_rels, infer_names_for_process_elements
from langgraph.graph import StateGraph, START, END
from typing import List, NotRequired
from typing_extensions import TypedDict
from parallel import MAX_PROCESSES
from graphdatascience import GraphDataScience as GDS
from graphdatascience.session.aura_graph_data_science import AuraGraphDataScience as AuraGDS
from graphdatascience.graph.graph_object import Graph as GDSGraph

def process_discovery_agent(graph_db, gds, session_name):
    class Comment(TypedDict):
        id: str
        content: str
        customer: NotRequired[bool]
    
    class Call(TypedDict):
        id: str
        messages: List[Comment]
    
    class ProcessElement(TypedDict):
        id: str
        # name: str | None
        description: str | None
        label: str | None
    
    class Observation(TypedDict):
        id: str
        description: str

    class State(TypedDict):
        calls: List[Call]
        observations: List[Observation]
        process_elements: List[ProcessElement]
        gds_graph: GDSGraph | None

    def get_calls(state):
        print("Getting calls from Neo4j...")
        calls = read_nodes(graph_db, label="Call")
        return {"calls": calls}
    
    def merge_process_observations_batch(i):
        def fn(state):
            print(f"Merging process element observations batch {i}")
            num_calls = len(state["calls"])
            calls = state["calls"][i * num_calls // MAX_PROCESSES:(i + 1) * num_calls // MAX_PROCESSES]
            write_process_observations(calls, graph_db)
            return {}
        return fn

    def get_process_observations(state):
        print("Getting process element observations from Neo4j...")
        # observations = graph_db.query("MATCH (o:Observation) RETURN o.id AS id, o.description AS description")
        observations = read_nodes(graph_db, label="Observation")
        return {"observations": observations}

    def embed_process_observations(state):
        print("Embedding process element observations...")
        embed_nodes(state["observations"], graph_db, label="Observation")
        return {}
    
    def map_transitions(state):
        print("Mapping TRANSITION relationships...")
        write_transition_rels(graph_db)
        return {}

    # def merge_entities_for_observations_batch(i):
    #     def fn(state):
    #         print(f"Merging entities for observations batch {i}")
    #         # Did not do seeding here, so we don't need to skip first process_element like in the ingest agent
    #         num_observations = len(state["observations"])
    #         observations = state["observations"][i * num_observations // MAX_PROCESSES:(i + 1) * num_observations // MAX_PROCESSES]
    #         write_entities(observations, graph_db, element_type="Observation")
    #         return {}
    #     return fn

    def project_gds_graph(state):
        print("Projecting GDS graph...")
        G = project_process_observations_to_gds(gds, session_name)
        return {"gds_graph": G}

    def discover_canonical_process_elements(state):
        print("Discovering canonical process elements...")
        process_community_detection(gds, state["gds_graph"])
        write_process_communities(graph_db)
        return {}

    def close_process_gds_session(state):
        print("Closing GDS session...")
        close_gds_session(gds, state["gds_graph"])
        return {"gds_graph": None}

    def lift_up_relationships(state):
        print("Creating lifted relationships...")
        write_lifted_rels(graph_db)
        return {}

    def get_canonical_process_elements(state):
        print("Getting process elements from Neo4j...")
        # process_elements = read_process_elements(graph_db)
        process_elements = read_nodes(graph_db, label="ProcessElement", return_label=True)
        return {"process_elements": process_elements}

    def name_canonical_process_elements_batch(i):
        def fn(state):
            print(f"Naming canonical process elements for batch {i}...")
            num_process_elements = len(state["process_elements"])
            process_elements = state["process_elements"][i * num_process_elements // MAX_PROCESSES:(i + 1) * num_process_elements // MAX_PROCESSES]
            infer_names_for_process_elements([pe["id"] for pe in process_elements], graph_db)
            return {}
        return fn

    agent_graph = StateGraph(State)

    agent_graph.add_node("get_calls", get_calls)
    agent_graph.add_edge(START, "get_calls")
    agent_graph.add_node("get_process_observations", get_process_observations)
    # agent_graph.add_edge(START, "get_process_observations")
    # merging process observations
    for j in range(MAX_PROCESSES):
        agent_graph.add_node(f"Merge process observations {j}", merge_process_observations_batch(j))
        agent_graph.add_edge("get_calls", f"Merge process observations {j}")
        agent_graph.add_edge(f"Merge process observations {j}", "get_process_observations")

    agent_graph.add_node("embed_process_observations", embed_process_observations)
    agent_graph.add_node("map_transitions", map_transitions)
    agent_graph.add_edge("get_process_observations", "embed_process_observations")
    agent_graph.add_edge("get_process_observations", "map_transitions")

    # merging extracted entities from process observations
    # for j in range(MAX_PROCESSES):
    #     agent_graph.add_node(f"Merge entities for observations batch {j}", merge_entities_for_observations_batch(j))
    #     agent_graph.add_edge("get_process_observations", f"Merge entities for observations batch {j}")
    #     agent_graph.add_edge(f"Merge entities for observations batch {j}", END)

    agent_graph.add_node("project_gds_graph", project_gds_graph)
    # agent_graph.add_edge(START, "project_gds_graph")
    agent_graph.add_edge("embed_process_observations", "project_gds_graph")
    agent_graph.add_edge("map_transitions", "project_gds_graph")
    agent_graph.add_node("discover_canonical_process_elements", discover_canonical_process_elements)
    agent_graph.add_edge("project_gds_graph", "discover_canonical_process_elements")
    agent_graph.add_node("close_process_gds_session", close_process_gds_session)
    agent_graph.add_edge("discover_canonical_process_elements", "close_process_gds_session")
    agent_graph.add_edge("close_process_gds_session", END)
    agent_graph.add_node("lift_up_relationships", lift_up_relationships)
    agent_graph.add_edge("discover_canonical_process_elements", "lift_up_relationships")
    # agent_graph.add_node("name_canonical_process_elements", name_canonical_process_elements)
    # agent_graph.add_edge("lift_up_relationships", "name_canonical_process_elements")
    # agent_graph.add_edge("name_canonical_process_elements", END)
    agent_graph.add_node("get_canonical_process_elements", get_canonical_process_elements)
    agent_graph.add_edge("lift_up_relationships", "get_canonical_process_elements")
    # agent_graph.add_edge("name_canonical_process_elements", "get_canonical_process_elements")

    for j in range(MAX_PROCESSES):
        agent_graph.add_node(f"Name canonical process elements {j}", name_canonical_process_elements_batch(j))
        agent_graph.add_edge("get_canonical_process_elements", f"Name canonical process elements {j}")
        agent_graph.add_edge(f"Name canonical process elements {j}", END)

    agent = agent_graph.compile()
    return agent