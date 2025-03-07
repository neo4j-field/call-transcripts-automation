"use client";
import { useRef, createContext, useContext } from "react";

// Create custom context for auto-scroll
const ScrollContext = createContext(null);

// Provide scroll to bottom functionality in ScrollProvider
export const ScrollProvider = ({ children }) => {
  const scrollRef = useRef(null);

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  };

  return (
    <ScrollContext.Provider value={{ scrollRef, scrollToBottom }}>
      {children}
    </ScrollContext.Provider>
  );
};

export const useScroll = () => {
  const { scrollRef, scrollToBottom } = useContext(ScrollContext);
  return { scrollRef, scrollToBottom };
};
