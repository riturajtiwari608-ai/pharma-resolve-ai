import {
  Bot,
  FileText,
  LoaderCircle,
  Paperclip,
  RotateCcw,
  Send,
  X,
} from "lucide-react";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  useDispatch,
  useSelector,
} from "react-redux";

import {
  addUserMessage,
  processCopilotMessage,
  processPdfUpload,
  resetComplaintWorkspace,
} from "../features/complaints/complaintSlice";

import MessageBubble from "./MessageBubble";

const MAX_FILE_SIZE =
  10 * 1024 * 1024;

export default function CopilotPanel() {
  const dispatch = useDispatch();

  const {
    complaintId,
    error,
    extractedTextPreview,
    isProcessing,
    isUploading,
    messages,
    processingLabel,
    selectedFileName,
    threadId,
    usedModel,
    warnings,
  } = useSelector(
    (state) => state.complaints,
  );

  const [message, setMessage] =
    useState("");

  const [selectedFile, setSelectedFile] =
    useState(null);

  const fileInputRef = useRef(null);
  const messageEndRef = useRef(null);

  const busy =
    isProcessing || isUploading;

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, processingLabel]);

  function submitMessage() {
    const cleanedMessage = message.trim();

    if (!cleanedMessage || busy) {
      return;
    }

    dispatch(
      addUserMessage(cleanedMessage),
    );

    dispatch(
      processCopilotMessage({
        message: cleanedMessage,
        complaintId,
        threadId,
        createDraft: true,
      }),
    );

    setMessage("");
  }

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      submitMessage();
    }
  }

  function handleFileChange(event) {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    if (file.type !== "application/pdf") {
      window.alert(
        "Please select a PDF complaint document.",
      );

      event.target.value = "";
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      window.alert(
        "PDF must be smaller than 10 MB.",
      );

      event.target.value = "";
      return;
    }

    setSelectedFile(file);
  }

  function removeSelectedFile() {
    setSelectedFile(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function uploadPdf() {
    if (!selectedFile || busy) {
      return;
    }

    dispatch(
      addUserMessage(
        `Uploaded complaint PDF: ${selectedFile.name}`,
      ),
    );

    dispatch(
      processPdfUpload({
        file: selectedFile,
        createDraft: true,
      }),
    );

    removeSelectedFile();
  }

  function resetWorkspace() {
    const confirmed = window.confirm(
      "Start a new complaint? Current unsaved workspace data will be cleared.",
    );

    if (confirmed) {
      dispatch(resetComplaintWorkspace());
      removeSelectedFile();
      setMessage("");
    }
  }

  return (
    <aside className="copilot-panel">
      <header className="copilot-header">
        <div className="copilot-title">
          <div className="copilot-logo">
            <Bot size={22} />
          </div>

          <div>
            <h2>PharmaResolve Copilot</h2>

            <span>
              AI complaint intake assistant
            </span>
          </div>
        </div>

        <button
          type="button"
          className="icon-button"
          title="Start new complaint"
          onClick={resetWorkspace}
        >
          <RotateCcw size={18} />
        </button>
      </header>

      <div className="copilot-meta">
        <span>
          {complaintId
            ? "Existing complaint mode"
            : "New complaint mode"}
        </span>

        {usedModel && (
          <span className="model-name">
            {usedModel}
          </span>
        )}
      </div>

      <div className="messages-container">
        {messages.map((item) => (
          <MessageBubble
            key={item.id}
            message={item}
          />
        ))}

        {busy && (
          <div className="processing-message">
            <LoaderCircle
              className="spin"
              size={18}
            />

            <span>
              {processingLabel ||
                "Processing complaint..."}
            </span>
          </div>
        )}

        {warnings.length > 0 && (
          <div className="warning-box">
            <strong>Review warnings</strong>

            <ul>
              {warnings.map(
                (warning, index) => (
                  <li key={`${warning}-${index}`}>
                    {warning}
                  </li>
                ),
              )}
            </ul>
          </div>
        )}

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        {extractedTextPreview && (
          <details className="text-preview">
            <summary>
              View extracted PDF text
            </summary>

            <pre>
              {extractedTextPreview}
            </pre>
          </details>
        )}

        <div ref={messageEndRef} />
      </div>

      <div className="copilot-composer">
        {selectedFile && (
          <div className="selected-file">
            <div>
              <FileText size={17} />

              <span>
                {selectedFile.name}
              </span>
            </div>

            <button
              type="button"
              onClick={removeSelectedFile}
              aria-label="Remove selected file"
            >
              <X size={16} />
            </button>
          </div>
        )}

        <textarea
          value={message}
          rows={4}
          placeholder={
            complaintId
              ? "Enter a correction, for example: Change affected quantity to 48 capsules..."
              : "Paste the raw customer complaint here..."
          }
          disabled={busy}
          onChange={(event) =>
            setMessage(event.target.value)
          }
          onKeyDown={handleKeyDown}
        />

        <div className="composer-actions">
          <div>
            <input
              ref={fileInputRef}
              id="complaint-pdf"
              className="hidden-file-input"
              type="file"
              accept=".pdf,application/pdf"
              disabled={busy}
              onChange={handleFileChange}
            />

            <label
              htmlFor="complaint-pdf"
              className="attachment-button"
            >
              <Paperclip size={18} />
              Attach PDF
            </label>
          </div>

          {selectedFile ? (
            <button
              type="button"
              className="primary-button"
              disabled={busy}
              onClick={uploadPdf}
            >
              {isUploading ? (
                <LoaderCircle
                  className="spin"
                  size={18}
                />
              ) : (
                <FileText size={18} />
              )}

              Analyse PDF
            </button>
          ) : (
            <button
              type="button"
              className="primary-button"
              disabled={
                busy || !message.trim()
              }
              onClick={submitMessage}
            >
              {isProcessing ? (
                <LoaderCircle
                  className="spin"
                  size={18}
                />
              ) : (
                <Send size={18} />
              )}

              Send
            </button>
          )}
        </div>

        <p className="composer-note">
          AI-generated output requires human QA
          review.
        </p>
      </div>
    </aside>
  );
}