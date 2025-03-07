import ContextMenu from "./ContextMenu";

const ChatComment = ({
  comment,
  sidebar = false,
  done = null,
  contextComments = null,
  useSuggestedComment = null,
}) => {
  return sidebar ? (
    <div className="chat chat-start text-lg">
      <div className="text-gray-800 font-semibold">
        <span>
          {comment.content}
          {done && contextComments && (
            <ContextMenu
              comment={comment}
              contextComments={contextComments}
              useSuggestedComment={useSuggestedComment}
            />
          )}
        </span>
      </div>
    </div>
  ) : (
    <div
      className={`chat ${
        comment.role === "user" ? "chat-end" : "chat-start"
      } text-lg`}
    >
      <div
        className={`chat-bubble ${
          comment.role === "user"
            ? "bg-blue-700 bg-gradient-to-r from-blue-400 to-blue-700 text-white"
            : "bg-gray-300 text-gray-800"
        }`}
      >
        {comment.content}
      </div>
    </div>
  );
};

export default ChatComment;
