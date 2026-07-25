const STATUS_LABELS = {
  draft: "Draft",
  pending_triage: "Pending Triage",
  ready_to_commit: "Ready to Commit",
  committed: "Committed",
  under_investigation: "Under Investigation",
  correction_ready: "Correction Ready",
  no_changes_detected: "No Changes Detected",
  processing: "Processing",
};

export default function StatusBadge({
  status = "draft",
}) {
  const normalizedStatus =
    status || "draft";

  const className = [
    "status-badge",
    `status-${normalizedStatus}`,
  ].join(" ");

  return (
    <span className={className}>
      {STATUS_LABELS[normalizedStatus] ||
        normalizedStatus
          .replaceAll("_", " ")
          .replace(/\b\w/g, (letter) =>
            letter.toUpperCase(),
          )}
    </span>
  );
}