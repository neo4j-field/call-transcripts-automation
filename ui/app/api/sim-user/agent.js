import { AzureChatOpenAI } from "@langchain/openai";
import { Annotation, StateGraph, START, END } from "@langchain/langgraph";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { z } from "zod";
import { getNeo4jSession } from "@/lib/neo4j";
import { v4 as uuidv4 } from "uuid";

const DEFAULT_k = 7;
const COMMENT_EMBEDDINGS_INDEX_NAME = "commentEmbeddings";

const Agent = (commentId) => {
  const GraphState = Annotation.Root({
    messages: Annotation({
      reducer: (x, y) => x.concat(y),
      default: () => [],
    }),
    embedding: Annotation({
      default: () => [],
    }),
    paths: Annotation({
      default: () => [],
    }),
    commentId: Annotation({
      default: () => "",
    }),
    resolved: Annotation({
      default: () => false,
    }),
    commentSample: Annotation({
      default: () => [],
    }),
  });

  const validateCommentId = async (state) => {
    console.log("Validating comment ID", commentId);
    const neo4jSession = getNeo4jSession();
    try {
      if (!commentId) {
        const result = await neo4jSession.run(
          `
          MATCH (c:Call)
          WITH c ORDER BY rand() LIMIT 1
          MATCH (c)-[:FIRST]->(comm)
          RETURN comm
          `
        );

        const comment = result.records[0].get("comm");
        commentId = comment.properties.id;
      } else {
        console.log("Validating commentID messages", [
          {
            role: "system",
            content: `
            Review the messages and determine if the user has addressed the most recent comment from their counterparty.
              View the final assistant message and then look if the final user message has adequately addressed it.
              Note that in some situations, the employee will need to ask for information - this can be considered a temporary resolution of the issue and the conversation can progress.
              If it has, return
                validated: true
              Otherwise return 
                validated: false
            `,
          },
          ...state.messages.map(({ role, content }) => ({
            role,
            content,
          })),
        ]);
        // We have a comment ID, so we need to validate it
        // This entails getting the comment and feeding it into an LLM, with the messages, to determine
        //   if the comment has been addressed
        // If so, move to the next comment in the conversation
        // If not, return the comment ID
        const messages = [
          {
            role: "system",
            content: `
            Review the messages and determine if the user has addressed the most recent comment from their counterparty.
              View the final assistant message and then look if the final user message has adequately addressed it.
              Note that in some situations, the employee will need to ask for information - this can be considered a temporary resolution of the issue and the conversation can progress.
              If it has, return
                validated: true
              Otherwise return 
                validated: false
            `,
          },
          ...state.messages.map(({ role, content }) => ({
            role,
            content,
          })),
        ];
        // Call OpenAI API to validate the latest comment (use fetch)
        const res = await fetch("https://api.openai.com/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
          },
          body: JSON.stringify({
            model: "gpt-4o-mini",
            messages,
            response_format: {
              type: "json_schema",
              json_schema: {
                name: "validate_latest_comment",
                schema: {
                  type: "object",
                  properties: {
                    validated: {
                      type: "boolean",
                    },
                  },
                  required: ["validated"],
                  additionalProperties: false,
                },
                strict: true,
              },
            },
          }),
        });
        const validation = await res.json();
        console.log("Validation:", validation);
        if (validation.validated) {
          // Move to the next comment in the conversation
          const result = await neo4jSession.run(
            `
            OPTIONAL MATCH (comm:Comment {id: $commentId})-[:NEXT]->()-[:NEXT]->(nextCustomerComm:Comment)
            RETURN nextCustomerComm AS nextComm
            `,
            { commentId }
          );
          const nextComment = result.records[0].get("nextComm");
          commentId = nextComment ? nextComment.properties.id : null;
          return { commentId, resolved: true };
        }
      }

      return { commentId };
    } finally {
      await neo4jSession.close();
    }
  };

  const getCommentSample = async (state) => {
    console.log("Comment sample", state.commentId);
    const neo4jSession = getNeo4jSession();
    try {
      const result = await neo4jSession.run(
        `
          // MATCH (comm:Comment {id: $commentId})
          // WITH comm
          // CALL db.index.vector.queryNodes($commentEmbeddings, $k, comm.embedding)
          // YIELD node AS similarComment
          // WITH similarComment
          // RETURN collect(similarComment.content) AS commentSample
          MATCH (comm:Comment {id: $commentId})
          MATCH (comm)-[:OBSERVED_STATE]->(:Observation:State)-[:IS_PROCESS_ELEMENT]->(:ProcessElement:State)<-[:IS_PROCESS_ELEMENT]-(:Observation:State)<-[:OBSERVED_STATE]-(similarComment:Comment)
          WITH similarComment
          ORDER BY vector.similarity.cosine(comm.embedding, similarComment.embedding) DESC
          LIMIT toInteger($k)
          RETURN collect(similarComment.content) AS commentSample
          `,
        {
          commentId: state.commentId,
          k: DEFAULT_k,
          commentEmbeddings: COMMENT_EMBEDDINGS_INDEX_NAME,
        }
      );

      const commentSample = result.records[0].get("commentSample");
      return { commentSample };
    } finally {
      await neo4jSession.close();
    }
  };

  const generate = async (state) => {
    console.log("Generating comment", state.commentId, state.commentSample);
    const promptTemplateString = `
      You are simulating a customer engaged with a customer service rep.
      You can see the comments up to this point in the message history, if any.
      From these, you can get a sense for the personality you're impersonating and the flow of the conversation.
      You should produce the next message in the conversation.
      Make a comment that makes sense in the context of the conversation.
      Additionally, see below a list of sample comments.
      These are comments that are similar in intent to the comment you should write next.
      They are examples you can leverage in producing your output.
    
      Comment Sample:
      {commentSample}
      `;

    const prompt = ChatPromptTemplate.fromMessages([
      ["system", promptTemplateString],
      ["placeholder", "{messages}"],
    ]);

    const llm = new AzureChatOpenAI({
      azureOpenAIApiDeploymentName: "gpt-4o",
      temperature: 0.8,
      streaming: true,
    });

    const chain = prompt.pipe(llm);
    const response = await chain.invoke({
      messages: state.messages,
      commentSample: state.commentSample.join("\n"),
    });

    return {
      messages: [
        {
          role: "assistant",
          content: response.content,
          id: uuidv4(),
          createdAt: new Date(),
        },
      ],
    };
  };

  const workflow = new StateGraph(GraphState)
    // define nodes
    .addNode("validateCommentId", validateCommentId)
    .addNode("getCommentSample", getCommentSample)
    .addNode("generate", generate);

  // define edges
  workflow.addEdge(START, "validateCommentId");
  workflow.addEdge("validateCommentId", "getCommentSample");
  workflow.addEdge("getCommentSample", "generate");
  workflow.addEdge("generate", END);

  const agent = workflow.compile();
  return agent;
};

export default Agent;
