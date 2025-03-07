"use client";
import { useState, useEffect, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { PulseLoader } from "react-spinners";
import ChatComment from "./ChatComment";
import { useScroll } from "@/contexts/ScrollContext";

const Sidebar = ({ comments, useSuggestedComment }) => {
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(false);
  const genRef = useRef(null);
  const { scrollRef, scrollToBottom } = useScroll();

  useEffect(() => {
    if (comments.length && comments[comments.length - 1].role === "assistant") {
      if (genRef.current) return;
      genRef.current = true;

      generate({
        messages,
        comments,
        setMessages,
        setPending,
        handleDone: () => {
          genRef.current = false;
          setMessages((prev) => [
            ...prev.slice(0, -1),
            { ...prev[prev.length - 1], done: true },
          ]);
        },
      });
    }
  }, [comments]);

  useEffect(() => {
    scrollToBottom();
  }, [comments, pending]);

  return (
    <div className="h-screen w-1/2 bg-transparent flex justify-center items-center">
      <div className="w-4/5 bg-transparent flex flex-col h-9/10">
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {messages.map((msg, i) => (
            <ChatComment
              key={msg.id}
              comment={msg}
              sidebar
              done={msg.done}
              contextComments={
                // Show context on last message only
                i === messages.length - 1 ? comments : null
              }
              useSuggestedComment={useSuggestedComment}
            />
          ))}
          {pending && <PulseLoader color="oklch(0.488 0.243 264.376)" />}

          <div ref={scrollRef} />
        </div>
      </div>
    </div>
  );
};

export default Sidebar;

// Functions
const generate = async ({
  messages,
  comments,
  setMessages,
  setPending,
  handleDone,
}) => {
  try {
    setPending(true);
    const res = await fetch(`/api/sidebar`, {
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
