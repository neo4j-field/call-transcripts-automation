import OpenAI, { AzureOpenAI } from "openai";

// const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const openai = new AzureOpenAI({
  endpoint: process.env.AZURE_OPENAI_ENDPOINT,
  apiKey: process.env.AZURE_OPENAI_API_KEY,
  apiVersion: "2025-01-01",
  deployment: "gpt-4o",
});

const callOpenAI = async ({
  messages,
  params = {},
  schema = {},
  stream = false,
  model = process.env.OPENAI_LLM,
}) => {
  const completion = await openai.chat.completions.create({
    model,
    messages,
    stream,
    ...params,
    ...schema,
  });
  if (stream) {
    const encoder = new TextEncoder();
    return new ReadableStream({
      async start(controller) {
        for await (const chunk of completion) {
          const content = chunk.choices[0]?.delta?.content || "";
          const queue = encoder.encode(content);
          controller.enqueue(queue);
        }
        controller.close();
      },
    });
  } else {
    return completion.choices[0].message.content;
  }
};

export { callOpenAI };
