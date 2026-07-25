import {
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
} from "lucide-react";

function severityLabel(value) {
  if (!value) {
    return "Unclassified";
  }

  return (
    value.charAt(0).toUpperCase() +
    value.slice(1)
  );
}

export default function RiskAssessmentCard({
  complaint,
}) {
  const hasAssessment =
    complaint.suggested_severity !==
      "unclassified" ||
    complaint.suggested_next_action ||
    complaint.initial_risk_assessment;

  if (!hasAssessment) {
    return (
      <section className="risk-card risk-empty">
        <BrainCircuit size={20} />

        <div>
          <h3>AI Copilot Risk Assessment</h3>

          <p>
            Submit complaint text or upload a PDF
            to generate a preliminary assessment.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="risk-card">
      <div className="section-title-row">
        <div className="section-icon">
          <BrainCircuit size={20} />
        </div>

        <div>
          <h3>AI Copilot Risk Assessment</h3>

          <p>
            Preliminary recommendation requiring
            Quality Assurance review.
          </p>
        </div>
      </div>

      <div className="risk-grid">
        <article className="risk-item">
          <span className="risk-label">
            Severity Suggested
          </span>

          <strong
            className={`severity severity-${complaint.suggested_severity}`}
          >
            <AlertTriangle size={16} />

            {severityLabel(
              complaint.suggested_severity,
            )}
          </strong>
        </article>

        <article className="risk-item">
          <span className="risk-label">
            Suggested Next Action
          </span>

          <div className="risk-value">
            <ArrowRight size={16} />

            <span>
              {complaint.suggested_next_action ||
                "Not available"}
            </span>
          </div>
        </article>
      </div>

      <article className="risk-description">
        <span className="risk-label">
          Initial Risk Assessment
        </span>

        <p>
          {complaint.initial_risk_assessment ||
            "Not available"}
        </p>
      </article>
    </section>
  );
}