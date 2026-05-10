"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Trash2, Play, History, Bot } from "lucide-react";
import { api, type Project, type ReconciliationRun, type AgentRun } from "@/lib/api";
import { errorMessage, formatDate, statusColor } from "@/lib/utils";
import { IntentEditor } from "@/components/intent-editor";

type Tab = "overview" | "reconciliations" | "agents";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [reconciliations, setReconciliations] = useState<ReconciliationRun[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [triggering, setTriggering] = useState(false);

  const fetchProject = useCallback(async () => {
    try {
      const data = await api.projects.get(id);
      setProject(data);
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchReconciliations = useCallback(async () => {
    try {
      const data = await api.projects.reconciliations(id);
      setReconciliations(data);
    } catch {}
  }, [id]);

  const fetchAgentRuns = useCallback(async () => {
    try {
      const data = await api.projects.agentRuns(id);
      setAgentRuns(data);
    } catch {}
  }, [id]);

  useEffect(() => {
    void Promise.resolve().then(() => {
      fetchProject();
      fetchReconciliations();
      fetchAgentRuns();
    });
  }, [fetchAgentRuns, fetchProject, fetchReconciliations]);

  const handleDelete = async () => {
    if (!confirm("Delete this project?")) return;
    try {
      await api.projects.delete(id);
      router.push("/dashboard");
    } catch (e: unknown) {
      setError(errorMessage(e));
    }
  };

  const handleTriggerAgent = async (agentType: string) => {
    setTriggering(true);
    try {
      await api.projects.triggerAgent(id, agentType, project?.intent_yaml || "");
      fetchAgentRuns();
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="p-8">
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {error || "Project not found"}
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: "overview", label: "Overview", icon: Play },
    { key: "reconciliations", label: "Reconciliations", icon: History },
    { key: "agents", label: "Agents", icon: Bot },
  ];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => router.push("/dashboard")} className="text-slate-500 hover:text-slate-300">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">{project.name}</h1>
            <span className={`text-xs px-2 py-1 rounded-full border ${statusColor(project.status)}`}>
              {project.status}
            </span>
          </div>
          {project.description && <p className="text-slate-400 mt-1">{project.description}</p>}
        </div>
        <button
          onClick={handleDelete}
          className="p-2 text-slate-500 hover:text-red-400 transition-colors"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Stack + URLs */}
      <div className="flex items-center gap-6 mb-6 text-sm">
        <span className="text-slate-500 uppercase tracking-wider">{project.stack}</span>
        {project.github_repo_url && (
          <a href={project.github_repo_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
            GitHub ↗
          </a>
        )}
        {project.deploy_url && (
          <a href={project.deploy_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
            Deploy ↗
          </a>
        )}
        <span className="text-slate-600">Updated {formatDate(project.updated_at)}</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-800 mb-6">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => {
                setActiveTab(tab.key);
                if (tab.key === "reconciliations") fetchReconciliations();
                if (tab.key === "agents") fetchAgentRuns();
              }}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab.key
                  ? "text-indigo-400 border-indigo-500"
                  : "text-slate-500 border-transparent hover:text-slate-300"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Quick actions */}
          <div className="flex gap-3">
            <button
              onClick={() => handleTriggerAgent("scaffold")}
              disabled={triggering}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white rounded-lg text-sm transition-colors border border-slate-700"
            >
              <Play className="h-4 w-4" />
              Scaffold Project
            </button>
            <button
              onClick={() => handleTriggerAgent("autofix")}
              disabled={triggering}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white rounded-lg text-sm transition-colors border border-slate-700"
            >
              <Bot className="h-4 w-4" />
              Run Autofix
            </button>
          </div>

          {/* Intent Editor */}
          <IntentEditor
            projectId={project.id}
            initialYaml={project.intent_yaml}
            onReconciled={() => {
              fetchProject();
              fetchReconciliations();
            }}
          />

          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
              <p className="text-sm text-slate-500">Reconciliations</p>
              <p className="text-2xl font-bold text-white mt-1">{reconciliations.length}</p>
            </div>
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
              <p className="text-sm text-slate-500">Agent Runs</p>
              <p className="text-2xl font-bold text-white mt-1">{agentRuns.length}</p>
            </div>
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
              <p className="text-sm text-slate-500">Stack</p>
              <p className="text-2xl font-bold text-white mt-1 capitalize">{project.stack}</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === "reconciliations" && (
        <div className="space-y-3">
          {reconciliations.length === 0 ? (
            <p className="text-slate-500 text-center py-12">No reconciliation runs yet. Edit the intent and click Reconcile.</p>
          ) : (
            reconciliations.map((run) => (
              <div key={run.id} className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${statusColor(run.status)}`}>
                      {run.status}
                    </span>
                    {run.dry_run && <span className="text-xs text-slate-500">Dry run</span>}
                  </div>
                  <span className="text-xs text-slate-500">{formatDate(run.created_at)}</span>
                </div>
                {run.resources_checked && run.resources_checked.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {run.resources_checked.map((r) => (
                      <span key={r} className="text-xs px-2 py-0.5 bg-slate-800 rounded text-slate-400 font-mono">{r}</span>
                    ))}
                  </div>
                )}
                {run.error_message && <p className="text-xs text-red-400 mt-2">{run.error_message}</p>}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "agents" && (
        <div className="space-y-3">
          {agentRuns.length === 0 ? (
            <p className="text-slate-500 text-center py-12">No agent runs yet. Use the buttons above to trigger one.</p>
          ) : (
            agentRuns.map((run) => (
              <div key={run.id} className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      run.agent_type === "scaffold" ? "bg-purple-500/20 text-purple-400 border-purple-500/30" :
                      run.agent_type === "autofix" ? "bg-amber-500/20 text-amber-400 border-amber-500/30" :
                      "bg-slate-500/20 text-slate-400 border-slate-500/30"
                    }`}>
                      {run.agent_type}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${statusColor(run.status)}`}>
                      {run.status}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">{formatDate(run.created_at)}</span>
                </div>
                {run.output && <p className="text-sm text-slate-400 mt-2 line-clamp-3">{run.output}</p>}
                {run.pr_url && (
                  <a href={run.pr_url} target="_blank" rel="noreferrer" className="text-indigo-400 text-sm mt-1 inline-block hover:underline">
                    View PR ↗
                  </a>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
