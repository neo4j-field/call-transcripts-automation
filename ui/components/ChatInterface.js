"use client";
import { useEffect } from "react";
import { PulseLoader } from "react-spinners";
import ChatInput from "./ChatInput";
import ChatComment from "./ChatComment";
import { useScroll } from "@/contexts/ScrollContext";

const ChatInterface = ({ comments, handleSendMessage, loading }) => {
  const { scrollRef, scrollToBottom } = useScroll();

  useEffect(() => {
    scrollToBottom();
  }, [comments, loading]);

  return (
    <div className="h-screen w-1/2 bg-transparent flex justify-center items-center">
      <div className="w-4/5 bg-base-100 rounded-xl shadow-lg flex flex-col h-9/10">
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {comments.map((comm) => (
            <ChatComment key={comm.id} comment={comm} />
          ))}
          {loading && (
            <PulseLoader color="oklch(0.488 0.243 264.376)" size={12} />
          )}
          <div ref={scrollRef} />
        </div>
        <ChatInput onSend={handleSendMessage} />
      </div>
    </div>
  );
};

export default ChatInterface;
