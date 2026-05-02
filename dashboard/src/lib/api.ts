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

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `API error: ${res.status}`);
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
    reconcile: (id: string, dryRun = false) =>
      fetchAPI<ReconciliationRun>(`/projects/${id}/reconcile`, { method: "POST", body: JSON.stringify({ dry_run: dryRun }) }),
    reconciliations: (id: string) =>
      fetchAPI<ReconciliationRun[]>(`/projects/${id}/reconciliations`),
    triggerAgent: (id: string, agentType: string, inputSpec: string) =>
      fetchAPI<AgentRun>(`/projects/${id}/agents`, { method: "POST", body: JSON.stringify({ agent_type: agentType, input_spec: inputSpec }) }),
    agentRuns: (id: string) =>
      fetchAPI<AgentRun[]>(`/projects/${id}/agents`),
  },
};
