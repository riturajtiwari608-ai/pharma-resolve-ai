import {
  AlertTriangle,
  CheckCircle2,
  X,
} from "lucide-react";

export default function CommitConfirmationModal({
  open,
  complaintNumber,
  isCommitting,
  onCancel,
  onConfirm,
}) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="modal-backdrop"
      role="presentation"
    >
      <section
        className="confirmation-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="commit-modal-title"
      >
        <header className="modal-header">
          <div className="modal-icon">
            <AlertTriangle size={22} />
          </div>

          <button
            type="button"
            className="icon-button"
            onClick={onCancel}
            disabled={isCommitting}
          >
            <X size={18} />
          </button>
        </header>

        <h2 id="commit-modal-title">
          Commit complaint to QMS?
        </h2>

        <p>
          You are about to commit{" "}
          <strong>
            {complaintNumber ||
              "this complaint"}
          </strong>{" "}
          to the QMS ledger.
        </p>

        <div className="modal-warning">
          <CheckCircle2 size={18} />

          <span>
            Confirm that all AI-extracted and
            manually edited information has been
            reviewed.
          </span>
        </div>

        <footer className="modal-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={onCancel}
            disabled={isCommitting}
          >
            Continue reviewing
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={onConfirm}
            disabled={isCommitting}
          >
            {isCommitting
              ? "Committing..."
              : "Confirm and Commit"}
          </button>
        </footer>
      </section>
    </div>
  );
}