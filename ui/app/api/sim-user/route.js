import { NextResponse } from "next/server";
import Agent from "./agent";

export const runtime = "edge";

const POST = async (request) => {
  const { commentId, messages } = await request.json();
  console.log("Sim User Comment ID:", commentId);
  console.log("Sim User Messages:", messages);

  try {
    const response = await Agent(commentId).invoke({ messages });
    console.log("Response:", response);
    console.log(response.messages[response.messages.length - 1]);

    return NextResponse.json({
      comment: response.messages[response.messages.length - 1],
      commentId: response.commentId,
    });
  } catch (error) {
    console.error("An error occurred:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
};

export { POST };
