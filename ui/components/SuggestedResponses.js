"use client";
import { useState, useEffect, useRef } from "react";
import { PulseLoader } from "react-spinners";
import { v4 as uuidv4 } from "uuid";

const SuggestedResponse = ({
  contextComments,
  suggestion,
  setSuggestion,
  useSuggestedComment,
}) => {
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(true);
  const [done, setDone] = useState(false);
  const genRef = useRef(null);

  useEffect(() => {
    if (genRef.current) return;
    genRef.current = true;

    generate({
      comments: contextComments,
      route: "suggested-response",
      setMessages: setMessages,
      setPending: setPending,
      handleDone: () => setDone(true),
    });
  }, []);

  useEffect(() => {
    if (done) {
      setSuggestion(messages[0].content);
    }
  }, [done]);

  return (
    <div className="w-full p-4 text-lg flex justify-between gap-4">
      {pending ? (
        <PulseLoader color="oklch(0.488 0.243 264.376)" size={10} />
      ) : (
        <p>{suggestion || messages[0].content}</p>
      )}
      <button
        className="btn btn-sm text-white rounded-full join-item bg-blue-700 self-center"
        disabled={pending}
        onClick={() => useSuggestedComment(suggestion || messages[0].content)}
      >
        Use Response
      </button>
    </div>
  );
};

const SuggestedResponses = ({
  contextComments,
  suggestions,
  setSuggestions,
  useSuggestedComment,
}) => {
  return (
    <div className="w-full h-full flex flex-col items-center gap-4">
      {[0, 1, 2].map((_, i) => (
        <SuggestedResponse
          key={i}
          contextComments={contextComments}
          suggestion={suggestions[i] === i ? null : suggestions[i]}
          setSuggestion={(s) =>
            setSuggestions((prev) => [...prev.slice(0, i), s, ...prev.slice(i)])
          }
          useSuggestedComment={useSuggestedComment}
        />
      ))}
    </div>
  );
};

export default SuggestedResponses;

// Functions
const generate = async ({
  messages,
  comments,
  route,
  setMessages,
  setPending,
  handleDone,
}) => {
  try {
    setPending(true);
    const res = await fetch(`/api/${route}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ messages, comments }),
    });

    if (!res.ok) {
      console.error("An error occurred", res.statusText);
      return;
    }

    // Handle stream response
    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");

    setPending(false);
    const messageId = uuidv4();

    setMessages((prev) => [
      ...prev,
      { id: messageId, role: "assistant", content: "" },
    ]);

    let done = false;
    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) {
        const chunk = decoder.decode(value);

        setMessages((prev) =>
          prev.map((message) =>
            message.id === messageId
              ? { ...message, content: message.content + chunk }
              : message
          )
        );
      }
    }
  } catch (error) {
    console.error("Error:", error);
  } finally {
    handleDone();
  }
};
