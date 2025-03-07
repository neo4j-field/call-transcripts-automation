"use client";
import { useState, useEffect, useRef } from "react";
import { MoonLoader } from "react-spinners";
import dynamic from "next/dynamic";
const InteractiveNvlWrapper = dynamic(
  () =>
    import(
      "@neo4j-nvl/react/lib/interactive-nvl-wrapper/InteractiveNvlWrapper"
    ).then((mod) => mod.InteractiveNvlWrapper),
  { ssr: false }
);

const mouseEventCallbacks = {
  onDrag: () => null,
  onPan: () => null,
  onZoom: () => null,
};

const colorNode = (node) => {
  if (node.label === "State") {
    return "#93c5fd";
  } else if (node.label === "Action") {
    return "#6ee7b7";
  } else if (node.label === "Resolution") {
    return "#fca5a5";
  } else {
    return "#d4d4d8";
  }
};

const ProcessMap = ({ nodes, rels, loading }) => {
  // const [nodes, setNodes] = useState([]);
  // const [rels, setRels] = useState([]);
  // const [loading, setLoading] = useState(true);
  // const fetchRef = useRef(null);

  // useEffect(() => {
  //   const fetchProcessMap = async () => {
  //     try {
  //       const res = await fetch("/api/process-map", {
  //         method: "POST",
  //         body: JSON.stringify({ comment: contextComment }),
  //         headers: {
  //           "Content-Type": "application/json",
  //         },
  //       });

  //       if (!res.ok) {
  //         throw new Error("Network response was not ok");
  //       }

  //       const data = await res.json();
  //       console.log("Data:", data);
  //       setNodes(data.nodes);
  //       setRels(data.rels);
  //     } catch (error) {
  //       console.error("Error:", error);
  //     } finally {
  //       setLoading(false);
  //     }
  //   };

  //   if (fetchRef.current) return;
  //   fetchRef.current = true;
  //   fetchProcessMap();
  // }, []);

  return (
    <div className="w-full h-full text-white flex justify-center items-center border-1 border-neutral-content relative">
      {loading ? (
        <MoonLoader color="oklch(0.488 0.243 264.376)" />
      ) : (
        <>
          <div className="bg-white rounded-lg shadow absolute top-1 left-1 z-10">
            {["State", "Action", "Resolution"].map((label) => (
              <div
                key={label}
                className="flex items-center gap-1 p-1 text-xs text-base-content/50"
              >
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: colorNode({ label }) }}
                />
                <div>{label}</div>
              </div>
            ))}
          </div>
          <div className="absolute inset-0">
            <InteractiveNvlWrapper
              nodes={nodes.map(({ label, description, ...others }) => ({
                ...others,
                color: colorNode({ label }),
              }))}
              rels={rels.map(({ probability, ...others }) => ({
                ...others,
              }))}
              mouseEventCallbacks={mouseEventCallbacks}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default ProcessMap;
