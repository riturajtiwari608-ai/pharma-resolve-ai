import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 90000,
  headers: {
    Accept: "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      "Unable to connect to the backend.";

    return Promise.reject(new Error(message));
  },
);

export async function sendCopilotMessage({
  message,
  complaintId = null,
  threadId = null,
  createDraft = true,
}) {
  const response = await apiClient.post("/copilot/message", {
    message,
    complaint_id: complaintId,
    thread_id: threadId,
    create_draft: createDraft,
  });

  return response.data;
}

export async function uploadComplaintPdf({
  file,
  createDraft = true,
}) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("create_draft", String(createDraft));

  const response = await apiClient.post(
    "/documents/analyze-pdf",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );

  return response.data;
}

export async function commitComplaint(complaintId) {
  const response = await apiClient.patch(
    `/complaints/${complaintId}`,
    {
      status: "committed",
    },
  );

  return response.data;
}