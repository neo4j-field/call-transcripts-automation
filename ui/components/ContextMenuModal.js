"use client";
import { useState, useEffect, useRef } from "react";
import ProcessMap from "./ProcessMap";
import SuggestedResponses from "./SuggestedResponses";
import { PulseLoader } from "react-spinners";

const ContextMenuModal = ({
  comment,
  handleClose,
  contextComments,
  useSuggestedComment,
}) => {
  const [tab, setTab] = useState("suggested-responses");
  const [processNodes, setProcessNodes] = useState([]);
  const [processRels, setProcessRels] = useState([]);
  const [processLoading, setProcessLoading] = useState(true);
  const [suggestions, setSuggestions] = useState([0, 1, 2]);
  const processFetchRef = useRef(null);

  useEffect(() => {
    const fetchProcessMap = async () => {
      try {
        const res = await fetch("/api/process-map", {
          method: "POST",
          body: JSON.stringify({
            comment: contextComments[contextComments.length - 1],
          }),
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!res.ok) {
          throw new Error("Network response was not ok");
        }

        const data = await res.json();
        console.log("Data:", data);
        setProcessNodes(data.nodes);
        setProcessRels(data.rels);
      } catch (error) {
        console.error("Error:", error);
      } finally {
        setProcessLoading(false);
      }
    };

    if (processFetchRef.current) return;
    processFetchRef.current = true;
    fetchProcessMap();
  }, []);

  return (
    <div className="modal modal-open">
      <div className="modal-box max-w-[80vw] w-[80vw] h-[90vh] flex flex-col items-center gap-4">
        {/* Close button */}
        <button
          className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2"
          onClick={handleClose}
        >
          ✕
        </button>

        <h4 className="font-bold text-base border-neutral-content border-b-1 pb-2 px-2">
          {comment.content}
        </h4>
        <div className="w-full flex justify-center items-center join gap-4">
          <button
            className={
              "btn btn-sm text-white rounded-full join-item" +
              (tab === "suggested-responses" ? " bg-blue-700" : " bg-blue-300")
            }
            onClick={(e) => {
              e.preventDefault();
              setTab("suggested-responses");
            }}
          >
            Suggested Responses
          </button>
          <button
            className={
              "btn btn-sm text-white rounded-full join-item" +
              (tab === "process-maps" ? " bg-blue-700" : " bg-blue-300")
            }
            onClick={(e) => {
              e.preventDefault();
              setTab("process-maps");
            }}
          >
            Process Maps{" "}
            {processLoading && (
              <span>
                <PulseLoader size={4} color="#fff" />
              </span>
            )}
          </button>
        </div>

        {/* Take up rest of space with content section */}
        <div className="flex-1 w-full flex flex-col items-center justify-center">
          <div className="w-full h-full flex justify-center items-center">
            {tab === "suggested-responses" ? (
              <SuggestedResponses
                contextComments={contextComments}
                suggestions={suggestions}
                setSuggestions={setSuggestions}
                useSuggestedComment={useSuggestedComment}
              />
            ) : (
              <ProcessMap
                nodes={processNodes}
                rels={processRels}
                loading={processLoading}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContextMenuModal;
