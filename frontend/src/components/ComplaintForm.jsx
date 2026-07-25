import {
  Building2,
  FlaskConical,
  PackageSearch,
  Save,
  Upload,
  UserRound,
} from "lucide-react";

import { useDispatch, useSelector } from "react-redux";
import { useState } from "react";

import {
  commitCurrentComplaint,
  saveCurrentComplaint,
  updateFormField,
} from "../features/complaints/complaintSlice";

import RiskAssessmentCard from "./RiskAssessmentCard";
import CommitConfirmationModal from "./CommitConfirmationModal";
import StatusBadge from "./StatusBadge";



function Field({
  label,
  name,
  value,
  onChange,
  type = "text",
  placeholder = "",
  disabled = false,
}) {
  return (
    <label className="form-field">
      <span>{label}</span>

      <input
        type={type}
        name={name}
        disabled={disabled}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(event) =>
          onChange(name, event.target.value)
        }
      />
    </label>
  );
}

function TextAreaField({
  label,
  name,
  value,
  onChange,
  placeholder = "",
  disabled = false,
}) {
  return (
    <label className="form-field form-field-full">
      <span>{label}</span>

      <textarea
        name={name}
        value={value ?? ""}
        placeholder={placeholder}
        disabled={disabled}
        rows={5}
        onChange={(event) =>
          onChange(name, event.target.value)
        }
      />
    </label>
  );
}

export default function ComplaintForm() {
  const dispatch = useDispatch();
  const [showCommitModal, setShowCommitModal] = useState(false);

  const {
    complaintData,
    complaintId,
    complaintNumber,
    isCommitting,
    isDirty,
    isSaving,
  } = useSelector(
    (state) => state.complaints,
  );
  const isReadOnly =
  complaintData.status === "committed";

  function handleFieldChange(field, value) {
    dispatch(
      updateFormField({
        field,
        value,
      }),
    );
  }

  function handleCommitRequest() {
  if (!complaintId) {
    return;
  }

  setShowCommitModal(true);
}

  function confirmCommit() {
   dispatch(
    commitCurrentComplaint(
      complaintId,
    ),
  ).then((result) => {
    if (!result.error) {
      setShowCommitModal(false);
    }
  });
}

  function handleManualSave() {
    if (!complaintId || !isDirty) {
      return;
    }

    dispatch(
      saveCurrentComplaint({
        complaintId,
        complaintData,
      }),
    );
  }

  const requiredFieldsComplete =
  Boolean(complaintData.customer_name) &&
  Boolean(complaintData.product_name) &&
  Boolean(complaintData.batch_lot_number) &&
  Boolean(complaintData.complaint_category) &&
  Boolean(complaintData.structured_defect_summary) &&
  Boolean(complaintData.suggested_next_action) &&
  Boolean(complaintData.initial_risk_assessment) &&
  complaintData.suggested_severity !== "unclassified";

const canCommit =
  Boolean(complaintId) &&
  requiredFieldsComplete &&
  complaintData.status !== "committed";

  {complaintId && !requiredFieldsComplete && (
  <span className="validation-warning">
    Complete the required complaint and AI assessment fields before committing.
  </span>
)}

  return (
    <section className="complaint-section">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">
            CUSTOMER COMPLAINT MODULE
          </div>

          <h1>Log Customer Complaint</h1>

          <p>
            Review AI-extracted information before
            committing it to the QMS ledger.
          </p>
        </div>

        <div className="header-status">
          {complaintNumber && (
            <span className="complaint-number">
              {complaintNumber}
            </span>
          )}

          <StatusBadge
            status={complaintData.status}
          />
        </div>
      </header>

      <div className="form-scroll-area">
        <section className={`form-section ${isReadOnly ? 'form-section-readonly' : ''}`}>
          <div className="form-section-heading">
            <UserRound size={19} />

            <div>
              <h2>Origin and Customer Details</h2>
              <p>
                Complaint origin and reporting
                customer.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <Field
              label="Complaint Source"
              name="complaint_source"
              value={
                complaintData.complaint_source
              }
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="Email, pharmacy, phone..."
            />

            <Field
              label="Customer Name"
              name="customer_name"
              value={complaintData.customer_name}
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="Customer or company name"
            />
          </div>
        </section>

        <section className={`form-section ${isReadOnly ? 'form-section-readonly' : ''}`}>
          <div className="form-section-heading">
            <PackageSearch size={19} />

            <div>
              <h2>
                Product and Batch Identification
              </h2>
              <p>
                Product, batch and affected quantity
                information.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <Field
              label="Product Name"
              name="product_name"
              value={complaintData.product_name}
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="Product name"
            />

            <Field
              label="Product Strength / Grade"
              name="product_strength_grade"
              value={
                complaintData.product_strength_grade
              }
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="500 mg, IP/BP..."
            />

            <Field
              label="Batch / Lot Number"
              name="batch_lot_number"
              value={
                complaintData.batch_lot_number
              }
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="Batch or lot number"
            />

            <div className="quantity-fields">
              <Field
                label="Affected Quantity"
                name="affected_quantity"
                value={
                  complaintData.affected_quantity
                }
                onChange={handleFieldChange}
                disabled={isReadOnly}
                type="number"
                placeholder="0"
              />

              <Field
                label="Unit"
                name="affected_quantity_unit"
                value={
                  complaintData
                    .affected_quantity_unit
                }
                onChange={handleFieldChange}
                disabled={isReadOnly}
                placeholder="capsules, kg..."
              />
            </div>

            <Field
              label="Manufacturing Date"
              name="manufacturing_date"
              value={
                complaintData.manufacturing_date
              }
              onChange={handleFieldChange}
              disabled={isReadOnly}
              type="date"
            />

            <Field
              label="Expiry Date"
              name="expiry_date"
              value={complaintData.expiry_date}
              onChange={handleFieldChange}
              disabled={isReadOnly}
              type="date"
            />
          </div>
        </section>

        <section className={`form-section ${isReadOnly ? 'form-section-readonly' : ''}`}>
          <div className="form-section-heading">
            <Building2 size={19} />

            <div>
              <h2>
                Facility and Material Impact
              </h2>
              <p>
                Manufacturing origin and impacted
                supporting material.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <Field
              label="Originating Site / Block"
              name="originating_site_block"
              value={
                complaintData
                  .originating_site_block
              }
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="Manufacturing Block A"
            />

            <Field
              label="Impacted Non-Product Material"
              name="impacted_non_product_material"
              value={
                complaintData
                  .impacted_non_product_material
              }
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="Bottle, blister, HDPE drum..."
            />
          </div>
        </section>

        <section className={`form-section ${isReadOnly ? 'form-section-readonly' : ''}`}>
          <div className="form-section-heading">
            <FlaskConical size={19} />

            <div>
              <h2>Defect Analysis</h2>
              <p>
                Complaint classification and
                structured defect summary.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <Field
              label="Complaint Category"
              name="complaint_category"
              value={
                complaintData.complaint_category
              }
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="Discoloration, contamination..."
            />

            <TextAreaField
              label="Structured Defect Summary"
              name="structured_defect_summary"
              value={
                complaintData
                  .structured_defect_summary
              }
              onChange={handleFieldChange}
              disabled={isReadOnly}
              placeholder="AI-generated complaint summary..."
            />
          </div>
        </section>

        <RiskAssessmentCard
          complaint={complaintData}
        />
      </div>

      <footer className="commit-footer">
        <div>
          <strong>Human review required</strong>

          <span>
            AI-generated values must be verified
            before final submission.
          </span>
        </div>

        <div className="footer-actions">
          <button
            type="button"
            className="secondary-button"
            disabled={
              !complaintId ||
              !isDirty ||
              isSaving ||
              complaintData.status === "committed"
            }
            onClick={handleManualSave}
          >
            <Upload size={18} />

            {isSaving
              ? "Saving..."
              : isDirty
                ? "Save Form Changes"
                : "Changes Saved"}
          </button>

          <button
            type="button"
            className="primary-button commit-button"
            disabled={
              !canCommit ||
              isCommitting ||
              isDirty
            }
            onClick={handleCommitRequest}
          >
            <Save size={18} />

            {complaintData.status === "committed"
              ? "Committed to QMS"
              : "Commit to QMS Ledger"}
          </button>
        </div>
      </footer>

      <CommitConfirmationModal
        open={showCommitModal}
        complaintNumber={complaintNumber}
        isCommitting={isCommitting}
        onCancel={() =>
          setShowCommitModal(false)
        }
        onConfirm={confirmCommit}
      />
    </section>
  );
}