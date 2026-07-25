import {
  AlertCircle,
  Bot,
  CheckCircle2,
  FileText,
  UserRound,
} from "lucide-react";

import StatusBadge from "./StatusBadge";

export default function MessageBubble({
  message,
}) {
  const isAssistant =
    message.role === "assistant";

  return (
    <article
      className={[
        "message-row",
        isAssistant
          ? "assistant-message-row"
          : "user-message-row",
      ].join(" ")}
    >
      <div className="message-avatar">
        {isAssistant ? (
          <Bot size={18} />
        ) : (
          <UserRound size={18} />
        )}
      </div>

      <div
        className={[
          "message-bubble",
          message.isError
            ? "message-error"
            : "",
        ].join(" ")}
      >
        <div className="message-role">
          {isAssistant
            ? "PharmaResolve Copilot"
            : "You"}
        </div>

        {message.filename && (
          <div className="message-file">
            <FileText size={16} />
            {message.filename}
          </div>
        )}

        <p>{message.content}</p>

        {message.status && (
          <StatusBadge status={message.status} />
        )}

        {message.fieldUpdates &&
          Object.keys(message.fieldUpdates)
            .length > 0 && (
            <div className="updated-fields">
              <CheckCircle2 size={15} />

              <span>
                Updated:{" "}
                {Object.keys(
                  message.fieldUpdates,
                )
                  .map((field) =>
                    field.replaceAll("_", " "),
                  )
                  .join(", ")}
              </span>
            </div>
          )}

        {message.isError && (
          <div className="message-error-label">
            <AlertCircle size={15} />
            Check backend logs for details.
          </div>
        )}
      </div>
    </article>
  );
}