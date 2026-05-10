const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api";

export interface Project {
  id: string;
  name: string;
  description: string;
  stack: string;
  status: string;
  intent_yaml: string;
  github_repo_url: string;
  deploy_url: string;
  created_at: string;
  updated_at: string;
}

export interface ReconciliationRun {
  id: string;
  project_id: string;
  status: string;
  dry_run: boolean;
  drifts_found: Record<string, number>;
  drifts_resolved: unknown[];
  resources_checked: string[];
  log: string;
  error_message: string;
  created_at: string;
}

export interface AgentRun {
  id: string;
  project_id: string;
  agent_type: string;
  status: string;
  input_spec: string;
  output: string;
  pr_url: string;
  created_at: string;
  completed_at: string | null;
}

export interface ProjectRun {
  id: string;
  tenant_id: string;
  project_id: string;
  run_type: string;
  status: string;
  title: string;
  summary: string;
  log: string;
  steps: { label: string; status: string; detail?: string }[];
  run_metadata: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ApiKey {
  id: string;
  provider: string;
  key_name: string;
  created_at: string;
}

export interface SetupProviderStatus {
  provider: string;
  label: string;
  required: boolean;
  status: string;
  source: string;
  has_key: boolean;
  required_env: string[];
  missing_env: string[];
  docs_url: string;
  next_action: string;
}

export interface SetupStatus {
  ready: boolean;
  connected: number;
  configured: number;
  missing_required: number;
  total: number;
  providers: SetupProviderStatus[];
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `API error: ${res.status}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export const api = {
  projects: {
    list: () => fetchAPI<{ projects: Project[]; total: number }>("/projects"),
    get: (id: string) => fetchAPI<Project>(`/projects/${id}`),
    create: (data: { name: string; description?: string; stack?: string; intent_yaml?: string }) =>
      fetchAPI<Project>("/projects", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Project>) =>
      fetchAPI<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) => fetchAPI<void>(`/projects/${id}`, { method: "DELETE" }),
    reconcile: (id: string, dryRun = false, intentYaml?: string) =>
      fetchAPI<ReconciliationRun>(`/projects/${id}/reconcile`, { method: "POST", body: JSON.stringify({ dry_run: dryRun, intent_yaml: intentYaml }) }),
    reconciliations: (id: string) =>
      fetchAPI<ReconciliationRun[]>(`/projects/${id}/reconciliations`),
    runs: (id: string) =>
      fetchAPI<ProjectRun[]>(`/projects/${id}/runs`),
    triggerAgent: (id: string, agentType: string, inputSpec: string) =>
      fetchAPI<AgentRun>(`/projects/${id}/agents`, { method: "POST", body: JSON.stringify({ agent_type: agentType, input_spec: inputSpec }) }),
    agentRuns: (id: string) =>
      fetchAPI<AgentRun[]>(`/projects/${id}/agents`),
  },
  keys: {
    list: () => fetchAPI<ApiKey[]>("/keys"),
    create: (data: { provider: string; key_name: string; key_value: string }) =>
      fetchAPI<ApiKey>("/keys", { method: "POST", body: JSON.stringify(data) }),
    delete: (id: string) => fetchAPI<void>(`/keys/${id}`, { method: "DELETE" }),
  },
  setup: {
    status: () => fetchAPI<SetupStatus>("/setup/status"),
  },
};
