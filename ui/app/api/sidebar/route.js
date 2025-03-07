import { NextResponse } from "next/server";
import Agent from "./agent";

export const runtime = "edge";

const POST = async (request) => {
  try {
    let { messages, comments } = await request.json();

    const eventStream = await Agent(comments).stream(
      { messages },
      { streamMode: ["messages", "updates"] }
    );

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        for await (const event of eventStream) {
          //       // First make sure it's a message update
          if (event[0] === "messages") {
            const token = event[1][0].content;
            controller.enqueue(encoder.encode(token));
          }
        }
        controller.close();
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
      },
    });
  } catch (error) {
    console.error("Error:", error);
    return NextResponse.json({ error: "An error occurred" }, { status: 500 });
  }
};

export { POST };
