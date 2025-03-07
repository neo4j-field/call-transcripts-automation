// app/api/getComment/route.js
import { NextResponse } from "next/server";
import { getNeo4jSession } from "@/lib/neo4j";

const GET = async (request) => {
  const session = getNeo4jSession();
  try {
    const result = await session.run(
      `
      MATCH (c:Call)
      WITH c LIMIT 1
      MATCH (c)-[:FIRST]->(comm)
      RETURN comm
      `
    );
    if (result.records.length === 0) {
      return NextResponse.json({ error: "No comment found" }, { status: 404 });
    }

    const comment = result.records[0].get("comm");
    return NextResponse.json({
      comment: {
        id: comment.properties.id,
        content: comment.properties.content,
        createdAt: Date.now(),
        role: "customer",
      },
    });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await session.close();
  }
};

export { GET };
