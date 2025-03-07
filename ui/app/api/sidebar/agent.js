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
    paths: Annotation({
      default: () => [],
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

  const retrievePaths = async (state) => {
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
        RETURN
          reduce(prob = probability, rel IN relationships(p) | prob * rel.probability) AS historicalProbability,
          [node IN nodes(p) | node.name] AS path
        ORDER BY historicalProbability DESC
        LIMIT 5
        `,
        {
          embedding: state.embedding,
          k: DEFAULT_k,
          commentEmbeddings: COMMENT_EMBEDDINGS_INDEX_NAME,
        }
      );
      const paths = queryResult.records.map((record) => ({
        path: record.get("path"),
        historicalProbability: record.get("historicalProbability"),
      }));
      return { paths };
    } finally {
      await neo4jSession.close();
    }
  };

  const generate = async (state) => {
    const promptTemplateString = `
      You are a conversational agent that is designed to help telecom customer service representatives talk to customers.
      Your job is to recommend the next action to the representative.
      You will see the list of comments up to this point as well as your own suggestion history to the rep.
      You will also get a list of recommended action paths the rep could follow, ordered by historical probability.
      Please consider these paths, consider the sentiment and context, and provide a recommendation.
      Put the recommendation into your own words and also advise on tone and approach.
      Only rely on the context you've been provided - don't make up any new information.
      Reply in 2 sentences or less.  Do not recommend language.  Just give advice.
    
      Comments:
      {comments}
    
      Action paths:
      {paths}
      `;

    const prompt = ChatPromptTemplate.fromMessages([
      ["system", promptTemplateString],
      ["placeholder", "{messages}"],
    ]);

    const llm = new ChatOpenAI({
      model: "gpt-4o",
      temperature: 0.8,
      streaming: true,
    });

    const chain = prompt.pipe(llm);
    const response = await chain.invoke({
      messages: state.messages,
      // Handle the last comment separately
      comments: `${comments
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
      paths: state.paths
        .map(({ path }) => `${path.map((action) => `${action}`).join(", ")}`)
        .join("\n"),
    });

    return { messages: [response] };
  };

  const workflow = new StateGraph(GraphState)
    // define nodes
    .addNode("embedComment", embedComment)
    .addNode("retrievePaths", retrievePaths)
    .addNode("generate", generate);

  // define edges
  workflow.addEdge(START, "embedComment");
  workflow.addEdge("embedComment", "retrievePaths");
  workflow.addEdge("retrievePaths", "generate");
  workflow.addEdge("generate", END);

  const agent = workflow.compile();
  return agent;
};

export default Agent;
