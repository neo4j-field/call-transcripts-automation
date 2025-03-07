from functions import write_transcripts, write_next_comments_relationships, write_entities, embed_nodes
from langgraph.graph import StateGraph, START, END
from typing import List, NotRequired
from typing_extensions import TypedDict
from parallel import MAX_PROCESSES

def transcript_processing_agent(file_uri, graph_db):
    class Comment(TypedDict):
        id: str
        content: str
        customer: NotRequired[bool]

    class State(TypedDict):
        comments: List[Comment]

    def ingest_transcripts(state):
        print("Ingesting transcripts...")
        comments = write_transcripts(file_uri, graph_db)
        return {"comments": comments}

    def link_transcript_comments(state):
        print("Linking transcript comments...")
        write_next_comments_relationships(graph_db)
        return {}
    
    def write_comment_embeddings(state):
        print("Embedding comments...")
        comments = state["comments"]
        embed_nodes(comments, graph_db)
        return {}

    agent_graph = StateGraph(State)
    # nodes
    agent_graph.add_node("ingest_transcripts", ingest_transcripts)
    agent_graph.add_node("link_transcript_comments", link_transcript_comments)
    agent_graph.add_node("write_comment_embeddings", write_comment_embeddings)
    # edges
    agent_graph.add_edge(START, "ingest_transcripts")
    agent_graph.add_edge("ingest_transcripts", "link_transcript_comments")
    agent_graph.add_edge("ingest_transcripts", "write_comment_embeddings")
    agent_graph.add_edge("link_transcript_comments", END)
    agent_graph.add_edge("write_comment_embeddings", END)

    agent = agent_graph.compile()
    return agent