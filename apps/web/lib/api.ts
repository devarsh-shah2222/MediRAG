const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface EvidenceItem {
  source_name: string;
  document_title: string;
  source_type: string;
  url: string | null;
  published_date: string | null;
  snippet: string;
  retrieval_score: number;
}

export interface ChatAction {
  id: string;
  label: string;
  type: string;
  target?: string | null;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  mode: "information" | "urgent" | "emergency_navigation";
  evidence: EvidenceItem[];
  actions: ChatAction[];
  disclaimer: string;
  language: string;
  emergency_contacts?: { emergency_number: string | null; poison_control: string | null; note: string } | null;
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError("We couldn't reach MediRAG right now. Please check your connection and try again.", 0);
  }

  if (!response.ok) {
    let detail = "Something went wrong. Please try again.";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse errors, use default detail
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export { ApiError };

export function sendChatMessage(
  payload: {
    message: string;
    conversation_id?: string | null;
    client_session_id: string;
    language?: string;
  },
  options?: { signal?: AbortSignal }
): Promise<ChatResponse> {
  return request("/api/chat", { method: "POST", body: JSON.stringify(payload), signal: options?.signal });
}

export function analyzeMedicine(payload: { query: string; language?: string }) {
  return request<any>("/api/medicine/analyze", { method: "POST", body: JSON.stringify(payload) });
}

export async function scanMedicineImage(file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/medicine/scan`, { method: "POST", body: form, credentials: "include" });
  return response.json();
}

export async function explainPrescription(file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/prescription/explain`, { method: "POST", body: form, credentials: "include" });
  return response.json();
}

export interface Provider {
  id: string;
  name: string;
  provider_type: string;
  specialty: string | null;
  address: string;
  city: string;
  phone: string | null;
  website: string | null;
  opening_hours: Record<string, string> | null;
  distance_km: number | null;
  accepts_emergency: boolean;
  is_demo: boolean;
}

export function listProviders(params: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return request<Provider[]>(`/api/providers?${query.toString()}`);
}

export function register(email: string, password: string) {
  return request("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function login(email: string, password: string) {
  return request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export function me() {
  return request("/api/auth/me");
}

export function submitFeedback(payload: { conversation_id?: string; message_id?: string; rating: number; comment?: string }) {
  return request("/api/feedback", { method: "POST", body: JSON.stringify(payload) });
}

export function listRagSources() {
  return request<any[]>("/api/rag/sources");
}

export function listRagDocuments() {
  return request<any[]>("/api/rag/documents");
}

export function reindexRag() {
  return request<{ reindexed_chunks: number }>("/api/rag/reindex", { method: "POST" });
}

export function prepareVisit(conversationId: string) {
  return request<{ summary_type: string; topics_discussed: string[]; suggested_questions: string[]; note: string }>(
    `/api/chat/${conversationId}/prepare-visit`
  );
}

export function getEmergencyInformation(region?: string) {
  return request<{ region: string; contacts: any }>(`/api/emergency-information${region ? `?region=${region}` : ""}`);
}
