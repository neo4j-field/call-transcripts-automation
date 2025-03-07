"use client";
import { useState } from "react";

const ChatInput = ({ onSend }) => {
  const [input, setInput] = useState("");

  const handleSubmit = () => {
    setInput("");
    if (!input.trim()) return;
    onSend(input);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      handleSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-base-300">
      <div className="flex gap-8 justify-center items-center">
        <textarea
          placeholder="Type a message..."
          className="textarea w-3/4"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyUp={handleKeyPress}
        />
        <button
          type="submit"
          className="btn bg-blue-700 text-white rounded-full"
        >
          Send
        </button>
      </div>
    </form>
  );
};

export default ChatInput;
