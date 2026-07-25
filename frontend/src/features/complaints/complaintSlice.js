import {
  createAsyncThunk,
  createSlice,
} from "@reduxjs/toolkit";

import {
  commitComplaint,
  getCorrectionHistory,
  saveManualComplaint,
  sendCopilotMessage,
  uploadComplaintPdf,
} from "./complaintApi";

import {
  initialAssistantMessage,
  initialComplaintData,
} from "../../utils/complaintDefaults";

function createMessage(role, content, extra = {}) {
  return {
    id: crypto.randomUUID(),
    role,
    type: "text",
    content,
    createdAt: new Date().toISOString(),
    ...extra,
  };
}

function normaliseComplaintData(payload) {
  if (!payload || typeof payload !== "object") {
    return {};
  }

  // Copilot new-complaint response can contain the saved complaint
  // directly, while the analysis-only response can contain extraction.
  if (payload.extraction) {
    return {
      ...payload.extraction,
      status:
        payload.processing_status === "ready_to_commit"
          ? "ready_to_commit"
          : "pending_triage",
    };
  }

  return payload;
}

export const processCopilotMessage = createAsyncThunk(
  "complaints/processCopilotMessage",
  async (
    {
      message,
      complaintId,
      threadId,
      createDraft = true,
    },
    { rejectWithValue },
  ) => {
    try {
      return await sendCopilotMessage({
        message,
        complaintId,
        threadId,
        createDraft,
      });
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

export const processPdfUpload = createAsyncThunk(
  "complaints/processPdfUpload",
  async (
    {
      file,
      createDraft = true,
    },
    { rejectWithValue },
  ) => {
    try {
      return await uploadComplaintPdf({
        file,
        createDraft,
      });
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

export const commitCurrentComplaint = createAsyncThunk(
  "complaints/commitCurrentComplaint",
  async (complaintId, { rejectWithValue }) => {
    try {
      return await commitComplaint(complaintId);
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);
export const saveCurrentComplaint =
  createAsyncThunk(
    "complaints/saveCurrentComplaint",
    async (
      {
        complaintId,
        complaintData,
      },
      { rejectWithValue },
    ) => {
      try {
        return await saveManualComplaint({
          complaintId,
          complaintData,
        });
      } catch (error) {
        return rejectWithValue(
          error.message,
        );
      }
    },
  );
  export const loadCorrectionHistory =
  createAsyncThunk(
    "complaints/loadCorrectionHistory",
    async (
      complaintId,
      { rejectWithValue },
    ) => {
      try {
        return await getCorrectionHistory(
          complaintId,
        );
      } catch (error) {
        return rejectWithValue(
          error.message,
        );
      }
    },
  );

const complaintSlice = createSlice({
  name: "complaints",

  initialState: {
    complaintData: initialComplaintData,

    complaintId: null,
    complaintNumber: null,
    threadId: null,

    messages: [initialAssistantMessage],

    isProcessing: false,
    isUploading: false,
    isCommitting: false,

    processingLabel: "",
    error: null,
    warnings: [],

    selectedFileName: null,
    extractedTextPreview: "",

    usedModel: null,
    fallbackUsed: false,

    isDirty: false,
    isSaving: false,
    correctionHistory: [],
  },

  reducers: {
    updateFormField(state, action) {
      const { field, value } = action.payload;

      state.complaintData[field] = value;
      state.isDirty = true;
    },

    addUserMessage(state, action) {
      state.messages.push(
        createMessage("user", action.payload),
      );
    },

    clearError(state) {
      state.error = null;
    },

    resetComplaintWorkspace(state) {
      state.complaintData = {
        ...initialComplaintData,
      };

      state.complaintId = null;
      state.complaintNumber = null;
      state.threadId = null;

      state.messages = [initialAssistantMessage];

      state.isProcessing = false;
      state.isUploading = false;
      state.isCommitting = false;

      state.processingLabel = "";
      state.error = null;
      state.warnings = [];

      state.selectedFileName = null;
      state.extractedTextPreview = "";

      state.usedModel = null;
      state.fallbackUsed = false;

      state.isDirty = false;
      state.isSaving = false;
      state.correctionHistory = [];
    },
  },

  extraReducers: (builder) => {
    builder
      // Copilot text message
      .addCase(processCopilotMessage.pending, (state) => {
        state.isProcessing = true;
        state.processingLabel =
          state.complaintId
            ? "Applying requested corrections..."
            : "Extracting complaint details...";

        state.error = null;
      })

      .addCase(
        processCopilotMessage.fulfilled,
        (state, action) => {
          state.isProcessing = false;
          state.processingLabel = "";

          const response = action.payload;

          state.threadId =
            response.thread_id || state.threadId;

          state.complaintId =
            response.complaint_id || state.complaintId;

          state.complaintNumber =
            response.complaint_number ||
            state.complaintNumber;

          state.warnings = response.warnings || [];
          state.usedModel = response.used_model || null;
          state.fallbackUsed =
            Boolean(response.fallback_used);

          const returnedComplaint =
            response.complaint_data;

          if (returnedComplaint) {
            const normalized =
              normaliseComplaintData(
                returnedComplaint,
              );

            state.complaintData = {
              ...state.complaintData,
              ...normalized,
            };
          }

          if (
            response.field_updates &&
            Object.keys(response.field_updates).length
          ) {
            state.complaintData = {
              ...state.complaintData,
              ...response.field_updates,
            };
          }

          if (response.processing_status) {
            state.complaintData.status =
              response.processing_status;
          }

          state.isDirty = false;

          state.messages.push(
            createMessage(
              "assistant",
              response.assistant_message ||
                "Complaint processed successfully.",
              {
                status:
                  response.processing_status,
                fieldUpdates:
                  response.field_updates || {},
              },
            ),
          );
        },
      )

      .addCase(
        processCopilotMessage.rejected,
        (state, action) => {
          state.isProcessing = false;
          state.processingLabel = "";

          state.error =
            action.payload ||
            "Complaint processing failed.";

          state.messages.push(
            createMessage(
              "assistant",
              `I could not process the request: ${
                action.payload ||
                "Unknown backend error"
              }`,
              {
                isError: true,
              },
            ),
          );
        },
      )

      // PDF upload
      .addCase(processPdfUpload.pending, (state) => {
        state.isUploading = true;
        state.processingLabel =
          "Uploading and analysing PDF...";

        state.error = null;
      })

      .addCase(
        processPdfUpload.fulfilled,
        (state, action) => {
          state.isUploading = false;
          state.processingLabel = "";

          const response = action.payload;

          state.complaintId =
            response.complaint_id ||
            state.complaintId;

          state.complaintNumber =
            response.complaint_number ||
            state.complaintNumber;

          state.extractedTextPreview =
            response.text_preview || "";

          state.selectedFileName =
            response.document?.original_filename ||
            state.selectedFileName;

          state.warnings = response.warnings || [];
          state.usedModel = response.used_model || null;
          state.fallbackUsed =
            Boolean(response.fallback_used);

          if (response.analysis?.extraction) {
            state.complaintData = {
              ...state.complaintData,
              ...response.analysis.extraction,
              status:
                response.complaint_status ||
                response.analysis
                  .processing_status ||
                "pending_triage",
            };
          }

          state.isDirty = false;

          state.messages.push(
            createMessage(
              "assistant",
              response.assistant_message ||
                "PDF analysis completed.",
              {
                status:
                  response.complaint_status,
                filename:
                  response.document
                    ?.original_filename,
              },
            ),
          );
        },
      )

      .addCase(
        processPdfUpload.rejected,
        (state, action) => {
          state.isUploading = false;
          state.processingLabel = "";

          state.error =
            action.payload ||
            "PDF analysis failed.";

          state.messages.push(
            createMessage(
              "assistant",
              `PDF analysis failed: ${
                action.payload ||
                "Unknown backend error"
              }`,
              {
                isError: true,
              },
            ),
          );
        },
      )

      // Commit complaint
      .addCase(
        commitCurrentComplaint.pending,
        (state) => {
          state.isCommitting = true;
          state.error = null;
        },
      )

      .addCase(
        commitCurrentComplaint.fulfilled,
        (state, action) => {
          state.isCommitting = false;
          state.isDirty = false;

          state.complaintData = {
            ...state.complaintData,
            ...action.payload,
            status: "committed",
          };

          state.messages.push(
            createMessage(
              "assistant",
              `Complaint ${
                action.payload.complaint_number ||
                state.complaintNumber ||
                ""
              } was committed to the QMS ledger.`,
              {
                status: "committed",
              },
            ),
          );
        },
      )

      .addCase(
        commitCurrentComplaint.rejected,
        (state, action) => {
          state.isCommitting = false;

          state.error =
            action.payload ||
            "Unable to commit complaint.";
        },
      )

      .addCase(
        saveCurrentComplaint.pending,
        (state) => {
          state.isSaving = true;
          state.error = null;
        },
      )

      .addCase(
        saveCurrentComplaint.fulfilled,
        (state, action) => {
          state.isSaving = false;
          state.isDirty = false;

          state.complaintData = {
            ...state.complaintData,
            ...action.payload,
            status:
              action.payload.status ||
              state.complaintData.status,
            };

            state.messages.push(
              createMessage(
                "assistant",
                "Manual form changes were saved successfully.",
                {
                  status: "saved",
                },
              ),
            );
          },
          )

      .addCase(
        saveCurrentComplaint.rejected,
        (state, action) => {
          state.isSaving = false;

          state.error =
            action.payload ||
            "Unable to save form changes.";
        },
      )

      .addCase(
        loadCorrectionHistory.fulfilled,
        (state, action) => {
          state.correctionHistory =
            action.payload.corrections || [];
          },
        )
      .addCase(
        loadCorrectionHistory.rejected,
        (state, action) => {
          state.error =
            action.payload ||
            "Unable to load correction history.";
        },
      );
    }
});


export const {
  addUserMessage,
  clearError,
  resetComplaintWorkspace,
  updateFormField,
} = complaintSlice.actions;

export default complaintSlice.reducer;