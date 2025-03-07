import os
from datetime import timedelta
from graphdatascience import GraphDataScience
from graphdatascience.session import AuraAPICredentials, GdsSessions, DbmsConnectionInfo, AlgorithmCategory

NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")
EXPECTED_SESSIONS_NODE_COUNT = 10000
EXPECTED_SESSIONS_RELATIONSHIP_COUNT = 100000

IS_AURA = os.environ.get("AURA", False) is True

def create_graph_data_science_session(session_name):
    if IS_AURA:
        client_id = os.environ["AURA_API_CLIENT_ID"]
        client_secret = os.environ["AURA_API_CLIENT_SECRET"]
        # If your account is a member of several tenants, you must also specify the tenant ID to use
        tenant_id = os.environ.get("AURA_API_TENANT_ID", None)
        sessions = GdsSessions(api_credentials=AuraAPICredentials(client_id, client_secret, tenant_id=tenant_id))
        # Estimate the memory needed for the GDS session
        memory = sessions.estimate(
            node_count=EXPECTED_SESSIONS_NODE_COUNT,
            relationship_count=EXPECTED_SESSIONS_RELATIONSHIP_COUNT,
            algorithm_categories=[AlgorithmCategory.CENTRALITY, AlgorithmCategory.COMMUNITY_DETECTION],
        )
        # Identify the AuraDB instance
        db_connection = DbmsConnectionInfo(
            uri=os.environ["NEO4J_URI"], username=os.environ["NEO4J_USERNAME"], password=os.environ["NEO4J_PASSWORD"]
        )
        # Create a GDS session!
        gds = sessions.get_or_create(
            # we give it a representative name
            session_name=session_name,
            memory=memory,
            db_connection=db_connection,
            ttl=timedelta(hours=5),
        )
        return gds
    else:
        gds = GraphDataScience(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
            database=NEO4J_DATABASE,
        )
        return gds