import { OpenAIEmbeddings, ChatOpenAI } from "@langchain/openai";
import { Annotation, StateGraph, START, END } from "@langchain/langgraph";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { getNeo4jSession } from "@/lib/neo4j";

const DEFAULT_k = 7;
const COMMENT_EMBEDDINGS_INDEX_NAME = "commentEmbeddings";

const Agent = (comments) => {
  const GraphState = Annotation.Root({
    messages: Annotation({
      reducer: (x, y) => x.concat(y),
      default: () => [],
    }),
    embedding: Annotation({
      default: () => [],
    }),
    action: Annotation({
      default: () => {},
    }),
    resolutions: Annotation({
      default: () => [],
    }),
    contents: Annotation({
      default: () => {},
    }),
  });

  const embedComment = async (state) => {
    const embedder = new OpenAIEmbeddings({
      model: "text-embedding-3-small",
      dimensions: 128,
    });
    const embedding = await embedder.embedDocuments([
      comments[comments.length - 1].content,
    ]);
    return { embedding: embedding[0] };
  };

  const retrieveActionAndResolutions = async (state) => {
    const neo4jSession = getNeo4jSession();
    try {
      const queryResult = await neo4jSession.run(
        `
        CALL db.index.vector.queryNodes($commentEmbeddings, $k, $embedding)
        YIELD node AS similarComment
        MATCH (similarComment)-[:OBSERVED_STATE]->()-[:IS_PROCESS_ELEMENT]->(pe)
        MATCH (pe)-[r:ACTION_SELECTION]->(action)
        WITH r.probability AS probability, action
        ORDER BY probability DESC
        LIMIT 1
        MATCH (res:ProcessElement:Resolution)
        MATCH p = shortestPath((action)-[:TRANSITION|ACTION_SELECTION|PROCESS_END*]->(res))
        WITH action,
          reduce(prob = probability, rel IN relationships(p) | prob * rel.probability) AS historicalProbability,
          [node IN nodes(p) | node] AS path
        ORDER BY historicalProbability DESC
        LIMIT 3
        RETURN action, collect(path[-1]) AS resolutions
        `,
        {
          embedding: state.embedding,
          k: DEFAULT_k,
          commentEmbeddings: COMMENT_EMBEDDINGS_INDEX_NAME,
        }
      );
      const { action, resolutions } = queryResult.records.map((record) => ({
        action: record.get("action"),
        resolutions: record.get("resolutions"),
      }))[0];
      return { action, resolutions };
    } finally {
      await neo4jSession.close();
    }
  };

  const getActionSamples = async (state) => {
    const neo4jSession = getNeo4jSession();
    try {
      const queryResult = await neo4jSession.run(
        `
        MATCH (action:ProcessElement:Action {id: $actionId})
        WITH action
        UNWIND $resolutionIds AS resolutionId
        MATCH (resolution:ProcessElement:Resolution {id: resolutionId})
        MATCH (action)<-[:IS_PROCESS_ELEMENT]-(:Observation)<-[:OBSERVED_ACTION]-(comm:Comment)<-[:NEXT*]-()<-[:FIRST]-(:Call)-[:OBSERVED_RESOLUTION]->(resolution)
        WITH resolution, comm
        ORDER BY rand()
        WITH resolution, collect(comm.content) AS contents
        RETURN resolution, contents[..2] AS contents
        `,
        {
          actionId: state.action.properties.id,
          resolutionIds: state.resolutions.map((res) => res.properties.id),
        }
      );
      const contents = queryResult.records.map((record) => ({
        resolution: record.get("resolution"),
        contents: record.get("contents"),
      }));
      return { contents };
    } finally {
      await neo4jSession.close();
    }
  };

  const generate = async (state) => {
    const promptTemplateString = `
      You are a conversational agent that is designed to help telecom customer service representatives talk to customers.
      Your job is to suggest a response in the conversation based on the context provided.
      This context includes both the conversation history as well as a list of comments made by the rep in similar situations.
      Your response should ideally be 2-3 sentences long and should be helpful and informative, but if it needs to be longer be as concise as possible.
      Respect the tone and sentiment of the call and respect the disposition of the customer.
      We want to be as helpful as possible to the customer and also have an eye towards positive outcomes for us.
      The example comments are organized by projected outcome, so decide what the best likely outcome is and respond accordingly.
    
      Conversation history:
      {conversation}
    
      {suggestions}
      `;

    const prompt = ChatPromptTemplate.fromMessages([
      ["system", promptTemplateString],
      // ["placeholder", "{messages}"],
    ]);

    const llm = new ChatOpenAI({
      model: "gpt-4o",
      temperature: 1.0,
      streaming: true,
    });

    console.log({
      // messages: state.messages,
      // Handle the last comment separately
      conversation: `${comments
        .slice(0, -1)
        .map(
          (comm) =>
            `${comm.role === "user" ? "Employee" : "Customer"}: ${comm.content}`
        )
        .join("\n")}
        
        Latest comment:
        ${
          comments[comments.length - 1].role === "user"
            ? "Employee"
            : "Customer"
        }: ${comments[comments.length - 1].content}`,
      suggestions: Object.entries(state.contents)
        .map(
          (res, conts) => `
        Outcome: ${res.name}
        ${conts.map((cont) => `Comment: ${cont}`).join("\n")}
      `
        )
        .join("\n\n"),
    });

    const chain = prompt.pipe(llm);
    const response = await chain.invoke({
      // messages: state.messages,
      // Handle the last comment separately
      conversation: `${comments
        .slice(0, -1)
        .map(
          (comm) =>
            `${comm.role === "user" ? "Employee" : "Customer"}: ${comm.content}`
        )
        .join("\n")}
        
        Latest comment:
        ${
          comments[comments.length - 1].role === "user"
            ? "Employee"
            : "Customer"
        }: ${comments[comments.length - 1].content}`,
      suggestions: Object.entries(state.contents)
        .map(
          (res, conts) => `
        Outcome: ${res.name}
        ${conts.map((cont) => `Comment: ${cont}`).join("\n")}
      `
        )
        .join("\n\n"),
    });

    return { messages: [response] };
  };

  const workflow = new StateGraph(GraphState)
    // define nodes
    .addNode("embedComment", embedComment)
    .addNode("retrieveActionAndResolutions", retrieveActionAndResolutions)
    .addNode("getActionSamples", getActionSamples)
    .addNode("generate", generate);

  // define edges
  workflow.addEdge(START, "embedComment");
  workflow.addEdge("embedComment", "retrieveActionAndResolutions");
  workflow.addEdge("retrieveActionAndResolutions", "getActionSamples");
  workflow.addEdge("getActionSamples", "generate");
  workflow.addEdge("generate", END);

  const agent = workflow.compile();
  return agent;
};

export default Agent;
