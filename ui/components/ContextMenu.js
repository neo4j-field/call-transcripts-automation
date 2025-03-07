"use client";
import { useState } from "react";
import ContextMenuModal from "./ContextMenuModal";

const ContextMenu = ({ comment, contextComments, useSuggestedComment }) => {
  const [hovered, setHovered] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <span className="pl-2">
        <span
          className={
            "btn btn-xs text-white p-2 rounded-full cursor-pointer" +
            (hovered ? " bg-blue-400 shadow" : " bg-blue-300 shadow-none")
          }
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onClick={() => setModalOpen((prev) => !prev)}
        >
          Context
        </span>
      </span>
      {modalOpen && (
        <ContextMenuModal
          comment={comment}
          contextComments={contextComments}
          handleClose={() => setModalOpen(false)}
          useSuggestedComment={(content) => {
            useSuggestedComment(content);
            setModalOpen(false);
          }}
        />
      )}
    </>
  );
};

export default ContextMenu;
