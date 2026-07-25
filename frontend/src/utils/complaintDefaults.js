export const initialComplaintData = {
  complaint_source: "",
  customer_name: "",

  product_name: "",
  product_strength_grade: "",
  batch_lot_number: "",

  affected_quantity: "",
  affected_quantity_unit: "",

  manufacturing_date: "",
  expiry_date: "",

  originating_site_block: "",
  impacted_non_product_material: "",

  complaint_category: "",
  structured_defect_summary: "",

  suggested_severity: "unclassified",
  suggested_next_action: "",
  initial_risk_assessment: "",

  ai_confidence_score: null,
  status: "draft",
  correction_count: 0,
};

export const initialAssistantMessage = {
  id: "welcome-message",
  role: "assistant",
  type: "text",
  content:
    "Ready to process a new complaint. Paste the raw customer complaint or upload a complaint PDF, and I will extract the data and prepare an initial risk assessment.",
};