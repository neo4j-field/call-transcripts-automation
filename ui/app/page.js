"use client";
import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatInterface from "@/components/ChatInterface";
import Sidebar from "@/components/Sidebar";
import NewCallModal from "@/components/NewCallModal";

const Home = () => {
  const [modalOpen, setModalOpen] = useState(true);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sampleCommentId, setSampleCommentId] = useState(null);

  const handleCloseModal = async () => {
    setModalOpen(false);
    await generate({
      commentId: sampleCommentId,
      comments,
      setComments,
      setSampleCommentId,
      setLoading,
    });
  };

  const handleSendMessage = (content) => {
    const userComment = {
      id: uuidv4(),
      content,
      role: "user",
      createdAt: new Date(),
    };
    setComments((prev) => [...prev, userComment]);
  };

  useEffect(() => {
    if (comments.length && comments[comments.length - 1].role === "user") {
      generate({
        commentId: sampleCommentId,
        comments,
        setComments,
        setSampleCommentId,
        setLoading,
      });
    }
  }, [comments]);

  const useSuggestedComment = (content) => {
    setComments((prev) => [
      ...prev,
      {
        id: uuidv4(),
        content,
        role: "user",
        createdAt: Date.now(),
      },
    ]);
  };

  return (
    <div className="h-screen w-screen flex justify-center items-center bg-transparent">
      <ChatInterface
        comments={comments}
        handleSendMessage={handleSendMessage}
        loading={loading}
      />
      <Sidebar comments={comments} useSuggestedComment={useSuggestedComment} />
      {modalOpen && <NewCallModal handleClose={handleCloseModal} />}
    </div>
  );
};

export default Home;

const generate = async ({
  commentId,
  comments,
  setComments,
  setSampleCommentId,
  setLoading,
}) => {
  try {
    setLoading(true);
    // Provide commentId and messages parameters in POST request
    const res = await fetch("/api/sim-user", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        commentId,
        messages: comments,
      }),
    });

    if (!res.ok) {
      throw new Error("Failed to fetch comment");
    }
    const data = await res.json();
    console.log("Fetched comment:", data.comment);
    setComments((prev) => [...prev, data.comment]);
    setSampleCommentId(data.commentId);
  } catch (error) {
    console.error("Error fetching comment:", error);
  } finally {
    setLoading(false);
  }
};
