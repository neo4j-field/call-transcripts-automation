import { NextResponse } from "next/server";
import { getNeo4jSession } from "@/lib/neo4j";

export const runtime = "edge";

const DEFAULT_k = 7;
const COMMENT_EMBEDDINGS_INDEX_NAME = "commentEmbeddings";

const POST = async (request) => {
  let { comment } = await request.json();
  console.log("Comment:", comment);
  const neo4jSession = getNeo4jSession();

  try {
    const queryResult = await neo4jSession.run(
      `
      WITH genai.vector.encode($content, $provider, { token: $token, model: "text-embedding-3-small", dimensions: 128 }) AS embedding
      CALL db.index.vector.queryNodes($commentEmbeddings, $k, embedding)
      YIELD node AS similarComment
      MATCH (similarComment)-[:OBSERVED_STATE]->()-[:IS_PROCESS_ELEMENT]->(pe)
      MATCH (pe)-[r:ACTION_SELECTION]->(action)
      WITH r.probability AS probability, action
      ORDER BY probability DESC
      LIMIT 1
      MATCH (res:ProcessElement:Resolution)
      MATCH p = shortestPath((action)-[:TRANSITION|ACTION_SELECTION|PROCESS_END*]->(res))
      WITH nodes(p) AS nodes, relationships(p) AS rels
      LIMIT 5
      // Process the paths into the format the frontend expects
      WITH collect(nodes) AS nodes, collect(rels) AS rels
      WITH apoc.coll.toSet(apoc.coll.flatten(nodes)) AS nodes, apoc.coll.toSet(apoc.coll.flatten(rels)) AS rels
      // Note that we have to stringify the IDs because the frontend expects them as strings
      RETURN
        [n IN nodes | {
          id: n.id + "",
          description: n.description,
          label: [lbl IN labels(n) WHERE lbl <> "ProcessElement" | lbl][0],
          captions: [{value: n.name}]
        }] AS nodes,
        [r IN rels | {
          id: elementId(r),
          from: startNode(r).id + "",
          to: endNode(r).id + "",
          probability: r.probability,
          captions: [{value: type(r)}]
        }] AS rels
      `,
      {
        content: comment.content,
        provider: "OpenAI",
        token: process.env.OPENAI_API_KEY,
        k: DEFAULT_k,
        commentEmbeddings: COMMENT_EMBEDDINGS_INDEX_NAME,
      }
    );
    const result = queryResult.records.map((record) => ({
      nodes: record.get("nodes"),
      rels: record.get("rels"),
    }))[0];

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error:", error);
    return NextResponse.json({ error: "An error occurred" }, { status: 500 });
  } finally {
    neo4jSession.close();
  }
};

export { POST };
