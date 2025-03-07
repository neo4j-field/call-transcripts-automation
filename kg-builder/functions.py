from vectors import embedder, ENTITY_VECTOR_INDEX_NAME, OBSERVATION_EMBEDDING_INDEX_NAME, VECTOR_EQUIVALENCE_THRESHOLD
from llms import entity_extractor_llm, state_observation_llm, action_selection_llm, decision_inference_llm, group_description_llm, resolution_inference_llm
from prompts import entity_extractor_prompt, state_observation_prompt, action_selection_prompt, decision_inference_prompt, group_description_prompt, resolution_inference_prompt
from gds import NEO4J_DATABASE, IS_AURA

def write_transcripts(file_uri, graph_db):
    print("Writing transcripts...")
    comments = graph_db.query("""
        CALL apoc.load.json($fileUri)
        YIELD value
        WITH value
        UNWIND value AS _call
        MERGE (c:Call {id: _call.call_id})
        WITH c, _call
        UNWIND _call.messages as m
        FOREACH (_ IN CASE WHEN m.sender = "customer" THEN [1] ELSE [] END |
            MERGE (:Customer {id: m.customer_id})
        )
        FOREACH (_ IN CASE WHEN m.sender = "representative" THEN [1] ELSE [] END |
            MERGE (:Representative {id: m.representative_id})
        )
        CREATE (comm:Comment {
            id: randomUUID(),
            timestamp: datetime(m.timestamp),
            content: m.message
        })
        WITH c, m, comm
        MATCH (u:Customer|Representative {
            id: coalesce(m.customer_id, m.representative_id)
        })
        CREATE (u)-[:MADE]->(comm)
        CREATE (c)-[:HAS]->(comm)
        RETURN comm.id AS id, comm.content AS content, u:Customer AS customer
    """, {"fileUri": file_uri})
    return comments

def write_next_comments_relationships(graph_db):
    print("Writing NEXT_COMMENTS relationships...")
    graph_db.query("""
        MATCH (c:Call)
        MATCH (c)-[:HAS]->(comm:Comment)
        WITH c, collect(comm) AS comments
        WITH c, apoc.coll.sortMaps(comments, "^timestamp") AS sortedComments
        MATCH (first:Comment {id: sortedComments[0].id})
        MERGE (c)-[:FIRST]->(first)
        WITH c, apoc.coll.pairsMin(sortedComments) AS exchanges
        UNWIND exchanges AS ex
        MATCH (a:Comment {id: ex[0].id})
        MATCH (b:Comment {id: ex[1].id})
        MERGE (a)-[:NEXT]->(b)
    """)

def read_nodes(graph_db, label="Call", return_label=False):
    if label == "Call":
        nodes = graph_db.query("""
            MATCH (c:Call)
            MATCH (c)-[:FIRST]->(:Comment)-[:NEXT]->*(comm:Comment)<-[:MADE]-(u)
            WITH c, collect({
                id: comm.id,
                content: comm.content,
                customer: u:Customer
            }) AS comments
            RETURN c.id AS id, comments
        """)
    else:
        nodes = graph_db.query(f"""
            MATCH (n:{label})
            RETURN
                n.id AS id,
                {"[lbl IN labels(n) WHERE NOT lbl IN ['Observation', 'ProcessElement']][0] AS label," if return_label else ""}
                coalesce(n.description, n.content) AS description
        """)
    return nodes

def embed_nodes(nodes, graph_db, label="Comment"):
    embeddings = embedder.embed_documents([node["content"] if "content" in node else node["description"] for node in nodes])
    print("Storing embeddings...")
    graph_db.query(f"""
        WITH $nodes AS nodes
        UNWIND nodes AS node
        MATCH (n:{label} {{id: node.id}})
        WITH n, node
        CALL db.create.setNodeVectorProperty(n, "embedding", node.embedding)
    """, {"nodes": [{**node, "embedding": embedding} for node, embedding in zip(nodes, embeddings)]})

def extract_entities(element):
	extracted_entities = entity_extractor_llm.invoke([
		("system", entity_extractor_prompt),
		("human", element["content"] if "content" in element else element["description"])
	])
	return [entity.model_dump() for entity in extracted_entities.entities]

def write_entities(elements, graph_db, label="Comment", seed=False):
    if seed:
        # Seeding will only be for comments, not for process elements
        # Comments are written first
        entities = extract_entities(elements[0])
        embeddings = embedder.embed_documents([entity["description"] for entity in entities])
        graph_db.query(f"""
            MATCH (c:{label} {{id: $elemId}})
            WITH c, $entities AS entities
            UNWIND entities AS entity
            MERGE (e:Entity {{name: entity.name}})
            ON CREATE SET e.description = entity.description
            MERGE (c)-[r:REF]->(e)
            SET r.quote = entity.quote
            WITH e, entity WHERE e.embedding IS null
            CALL db.create.setNodeVectorProperty(e, "embedding", entity.embedding)
        """, {"elemId": elements[0]["id"], "entities": [{**entity, "embedding": embedding} for entity, embedding in zip(entities, embeddings)]})
    else:
        for elem in elements:
            entities = extract_entities(elem)
            embeddings = embedder.embed_documents([entity["description"] for entity in entities])
            graph_db.query(f"""
                MATCH (n:{label} {{id: $elemId}})
                WITH n, $entities AS entities
                UNWIND entities AS entity
                WITH n, entity
                CALL db.index.vector.queryNodes($ENTITY_VECTOR_INDEX_NAME, 1, entity.embedding)
                YIELD node AS similarEntity, score
                WITH n, entity, similarEntity, score
                FOREACH (_ IN CASE WHEN score > $VECTOR_EQUIVALENCE_THRESHOLD THEN [1] ELSE [] END |
                    MERGE (n)-[r:REF]->(similarEntity)
                    SET r.extracted = entity.name, r.similarity = score, r.quote = entity.quote
                )
                FOREACH (_ IN CASE WHEN score <= $VECTOR_EQUIVALENCE_THRESHOLD THEN [1] ELSE [] END |
                    MERGE (e:Entity {{name: entity.name}})
                    SET e.description = entity.description
                    MERGE (n)-[r:REF]->(e)
                    SET r.quote = entity.quote
                )
                WITH score, entity
                UNWIND CASE WHEN score <= $VECTOR_EQUIVALENCE_THRESHOLD THEN [1] ELSE [] END AS _
                MATCH (e:Entity {{name: entity.name}})
                CALL db.create.setNodeVectorProperty(e, "embedding", entity.embedding)
            """, {
                "elemId": elem["id"],
                "entities": [{**entity, "embedding": embedding} for entity, embedding in zip(entities, embeddings)],
                "ENTITY_VECTOR_INDEX_NAME": ENTITY_VECTOR_INDEX_NAME,
                "VECTOR_EQUIVALENCE_THRESHOLD": VECTOR_EQUIVALENCE_THRESHOLD
            })

def extract_process_elements(call):
    state_observations = []
    action_selections = []
    # inferred_decisions = []
    inferred_resolutions = []
    for i, comment in enumerate(call["comments"]):
        # The "subcall" at position i is the list of comments up to and including the comment at position i
        # We don't need this list itself, we'll just put it into a transcript string for the LLM
        subcall_transcript = f"""
            CALL TRANSCRIPT:
            {"\n".join(
                [f"{"Customer" if comm["customer"] else "Employee"}: {comm["content"]}"
                for comm in call["comments"][:i]]
            )}

            LATEST COMMENT:
            {"Customer" if comment["customer"] else "Employee"}: {comment["content"]}
            """
        # for each comment in the call such that comment.customer is True, we need to
        #   get all the comments up to and including that comment in a list, and then
        #   feed that list into the state observation LLM
        if comment["customer"]:
            extracted_state = state_observation_llm.invoke([
                ("system", state_observation_prompt),
                ("human", subcall_transcript)
            ])
            state_observations.append({
                "comment_id": comment["id"],
                "description": extracted_state.state
            })
        # for each comment in the call such that comment.customer is False, we need to
        #   get all the comments up to and including that comment in a list, and then
        #   feed that list into the action selection LLM
        else:
            extracted_action = action_selection_llm.invoke([
                ("system", action_selection_prompt),
                ("human", subcall_transcript)
            ])
            action_selections.append({
                "comment_id": comment["id"],
                "description": extracted_action.action
            })
            # also need to feed the action into the decision inference LLM
            # if i > 0:
            #     extracted_decision = decision_inference_llm.invoke([
            #         ("system", decision_inference_prompt),
            #         ("human", subcall_transcript),
            #     ])
            #     inferred_decisions.append({
            #         "state_comment_id": call["comments"][i - 1]["id"],
            #         "action_comment_id": comment["id"],
            #         "description": extracted_decision.decision
            #     })
            # fetch the resolution node for the call
            if i == len(call["comments"]) - 1:
                extracted_resolution = resolution_inference_llm.invoke([
                    ("system", resolution_inference_prompt),
                    ("human", subcall_transcript)
                ])
                inferred_resolutions.append({
                    "call_id": call["id"],
                    "last_comment_id": comment["id"],
                    "description": extracted_resolution.resolution
                })
    return state_observations, action_selections, inferred_resolutions
    # return state_observations, action_selections, inferred_decisions

def write_process_observations(calls, graph_db):
    for call in calls:
        # state_observations, action_selections, inferred_decisions = extract_process_elements(call)
        state_observations, action_selections, inferred_resolutions = extract_process_elements(call)
        # Create observations
        graph_db.query("""
            UNWIND $states AS state
            MATCH (comm:Comment {id: state.comment_id})
            CREATE (so:Observation {id: randomUUID()})
            MERGE (comm)-[:OBSERVED_STATE]->(so)
            SET so:State, so.description = state.description
        """, {
            "states": state_observations
        })
        # Create actions
        graph_db.query("""
            UNWIND $actions AS action
            MATCH (comm:Comment {id: action.comment_id})
            CREATE (ao:Observation {id: randomUUID()})
            MERGE (comm)-[:OBSERVED_ACTION]->(ao)
            SET ao:Action, ao.description = action.description
        """, {
            "actions": action_selections
        })
        # Create decisions
        # graph_db.query("""
        #     UNWIND $decisions AS decision
        #     MATCH (:Comment {id: decision.state_comment_id})-[:OBSERVED_STATE]->(so:Observation)
        #     MATCH (rep:Representative)-[:MADE]->(:Comment {id: decision.action_comment_id})-[:OBSERVED_ACTION]->(ao:Observation)
        #     CREATE (do:Observation {id: randomUUID()})
        #     SET do:Decision, do.description = decision.description
        #     MERGE (so)-[:INFERRED_STATE_DECISION]->(do)
        #     MERGE (do)-[:INFERRED_DECISION_ACTION]->(ao)
        #     MERGE (rep)-[:DECISION_OBSERVATION]->(do)
        # """, {
        #     "decisions": inferred_decisions
        # })
        # Create resolutions
        graph_db.query("""
            UNWIND $resolutions AS resolution
            MATCH (c:Call {id: resolution.call_id})
            CREATE (ro:Observation {id: randomUUID()})
            MERGE (c)-[:OBSERVED_RESOLUTION]->(ro)
            SET ro:Resolution, ro.description = resolution.description
        """, {
            "resolutions": inferred_resolutions
        })

def embed_observations(observations, graph_db):
    embeddings = embedder.embed_documents([obs["description"] for obs in observations])
    print("Storing observation embeddings...")
    graph_db.query("""
        WITH $observations AS observations
        UNWIND observations AS obs
        MATCH (o:Observation {id: obs.id})
        WITH o, obs
        CALL db.create.setNodeVectorProperty(o, "embedding", obs.embedding)
    """, {"observations": [{**obs, "embedding": embedding} for obs, embedding in zip(observations, embeddings)]})

def write_transition_rels(graph_db):
    graph_db.query("""
        MATCH (so:Observation)<-[:OBSERVED_STATE]-(c0:Comment)-[:NEXT]->(c1:Comment)-[:OBSERVED_ACTION]->(ao:Observation)
        CALL {
            WITH so, ao
            MERGE (so)-[:OBSERVED_ACTION_SELECTION]->(ao)
        } IN TRANSACTIONS OF 1000 ROWS
    """)
    graph_db.query("""
        MATCH (ao:Observation)<-[:OBSERVED_ACTION]-(c0:Comment)-[:NEXT]->(c1:Comment)-[:OBSERVED_STATE]->(so:Observation)
        CALL {
            WITH so, ao
            MERGE (ao)-[:OBSERVED_TRANSITION]->(so)
        } IN TRANSACTIONS OF 1000 ROWS
    """)
    graph_db.query("""
        MATCH (ro:Resolution)<-[:OBSERVED_RESOLUTION]-(c:Call)-[:FIRST]->()-[:NEXT]->*(last)
        WHERE NOT EXISTS {
            (last)-[:NEXT]->()
        }
        MATCH (last)-->(obs:Observation)
        CALL {
            WITH ro, obs
            MERGE (obs)-[:OBSERVED_PROCESS_END]->(ro)
        } IN TRANSACTIONS OF 1000 ROWS
    """)

def project_process_observations_to_gds(gds, session_name):
    threshold = VECTOR_EQUIVALENCE_THRESHOLD
    query = f"""
    // CYPHER runtime=parallel  // Use parallel runtime in Aura Business Crtical or Virtual Dedicated Cloud
    MATCH (obs:Observation)
    OPTIONAL MATCH (similarObs:Observation)
    WHERE elementId(obs) <> elementId(similarObs)
    // Get all vectors within a certain cosine similarity threshold
    AND vector.similarity.cosine(obs.embedding, similarObs.embedding) > {threshold}
    AND ((obs:State AND similarObs:State)
    OR (obs:Action AND similarObs:Action)
    OR (obs:Resolution AND similarObs:Resolution))
    WITH obs, similarObs, vector.similarity.cosine(obs.embedding, similarObs.embedding) AS score
    RETURN gds.graph.project{".remote" if IS_AURA else ""}({"" if IS_AURA else "$graph_name, "}obs, similarObs, {{
        sourceNodeProperties: {{}},
        targetNodeProperties: {{}},
        sourceNodeLabels: labels(obs),
        targetNodeLabels: labels(similarObs),
        relationshipType: "SIMILAR",
        // Normalize the score to be between 0 and 1
        relationshipProperties: {{score: (score - {threshold}) / (1 - {threshold})}}
    }}{"" if IS_AURA else """,{
            undirectedRelationshipTypes: ["*"]
        }
    """})
    """
    if IS_AURA:
        G, _ = gds.graph.project(session_name, query, undirected_relationship_types=["*"])
    else:
        G, _ = gds.graph.cypher.project(query, database=NEO4J_DATABASE, graph_name=session_name)
    return G

def process_community_detection(gds, graph):
    gds.pageRank.write(graph, writeProperty="centrality")
    gds.wcc.write(graph, writeProperty="community")
    # gds.louvain.write(graph, writeProperty="community", relationshipWeightProperty="score")
    # gds.leiden.write(graph, writeProperty="community", relationshipWeightProperty="score", gamma=3.0)

def write_process_communities(graph_db):
    graph_db.query("""
        MATCH (obs:Observation)
        WITH obs, obs.community AS community
        MERGE (pe:ProcessElement {id: community})
        MERGE (obs)-[:IS_PROCESS_ELEMENT]->(pe)
        SET obs.community = null
    """)
    graph_db.query("""
        MATCH (pe:ProcessElement)
        WHERE EXISTS {
            (pe)<-[:IS_PROCESS_ELEMENT]-(:State)
        }
        SET pe:State
        WITH DISTINCT 1 AS resetCardinality
        MATCH (pe:ProcessElement)
        WHERE EXISTS {
            (pe)<-[:IS_PROCESS_ELEMENT]-(:Action)
        }
        SET pe:Action
        WITH DISTINCT 1 AS resetCardinality
        MATCH (pe:ProcessElement)
        WHERE EXISTS {
            (pe)<-[:IS_PROCESS_ELEMENT]-(:Resolution)
        }
        SET pe:Resolution
    """)

def close_gds_session(gds, graph):
    if IS_AURA:
        gds.delete()
    else:
        graph.drop()
        gds.close()

def write_lifted_rels(graph_db):
    graph_db.query("""
        MATCH (pe0:ProcessElement)<-[:IS_PROCESS_ELEMENT]-(o0:Observation)-[r]->(o1:Observation)-[:IS_PROCESS_ELEMENT]->(pe1:ProcessElement)
        WITH *,
            CASE type(r)
                WHEN "OBSERVED_ACTION_SELECTION" THEN "ACTION_SELECTION"
                WHEN "OBSERVED_TRANSITION" THEN "TRANSITION"
                ELSE "PROCESS_END"
            END AS relType
        CALL apoc.merge.relationship(
            pe0, relType, {}, {num: 0}, pe1
        ) YIELD rel
        WITH rel
        // Tracking number of connections between any given pair of process elements
        SET rel.num = rel.num + 1
    """)
    # Edge probabilities in the process map
    graph_db.query("""
        MATCH (pe:ProcessElement)
        MATCH (comm:Comment)-->(:Observation)-[:IS_PROCESS_ELEMENT]->(pe)
        WITH pe, count(comm) AS numComments
        MATCH (pe)-[r]->(:ProcessElement)
        SET r.probability = 1.0 * r.num / numComments
    """)

def infer_names_for_process_elements(process_element_ids, graph_db):
    process_elements = graph_db.query("""
        UNWIND $processElementIds AS id
        MATCH (pe:ProcessElement {id: id})
        MATCH (pe)<-[:IS_PROCESS_ELEMENT]-(o:Observation)
        WITH pe, collect({
            description: o.description,
            centrality: o.centrality
        }) AS observationDescriptions
        RETURN
            pe.id AS processElementId,
            [label IN labels(pe) WHERE label IN ["State", "Action", "Resolution"]][0] AS label,
            apoc.coll.sortMaps(observationDescriptions, "centrality") AS observationDescriptions
    """, {"processElementIds": process_element_ids})
    for process_element in process_elements:
        group_description_result = group_description_llm.invoke([
            ("system", group_description_prompt(process_element["label"])),
            ("human", "\n".join([f"{obs["description"]} ---- Importance Score: {obs["centrality"]}" for obs in process_element["observationDescriptions"]]))
        ])
        name = group_description_result.name
        description = group_description_result.description
        embedding = embedder.embed_documents([description])[0]
        pe_info = {
            "id": process_element["processElementId"],
            "name": name,
            "description": description,
            "embedding": embedding
        }
        graph_db.query("""
            MATCH (pe:ProcessElement {id: $id})
            SET pe.name = $name, pe.description = $description
            WITH pe
            CALL db.create.setNodeVectorProperty(pe, "embedding", $embedding)
        """, pe_info)