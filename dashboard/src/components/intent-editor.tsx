"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { api, type ReconciliationRun } from "@/lib/api";
import { errorMessage } from "@/lib/utils";

export function IntentEditor({
  projectId,
  initialYaml,
  onReconciled,
}: {
  projectId: string;
  initialYaml: string;
  onReconciled?: () => void;
}) {
  const [yaml, setYaml] = useState(initialYaml || "");
  const [reconciling, setReconciling] = useState(false);
  const [dryRun, setDryRun] = useState(true);
  const [result, setResult] = useState<ReconciliationRun | null>(null);
  const [error, setError] = useState("");

  const handleReconcile = async () => {
    setReconciling(true);
    setError("");
    setResult(null);
    try {
      const run = await api.projects.reconcile(projectId, dryRun, yaml);
      setResult(run);
      onReconciled?.();
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setReconciling(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-300">.powerhouse.yml</h3>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="rounded bg-slate-800 border-slate-600"
            />
            Dry run
          </label>
          <button
            onClick={handleReconcile}
            disabled={reconciling}
            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {reconciling ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Reconcile
          </button>
        </div>
      </div>

      <textarea
        value={yaml}
        onChange={(e) => setYaml(e.target.value)}
        className="w-full h-48 px-4 py-3 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono text-sm focus:outline-none focus:border-indigo-500 resize-none"
        spellCheck={false}
      />

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {result && (
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <span className={`text-xs px-2 py-0.5 rounded-full border ${
              result.status === "synced" ? "bg-green-500/20 text-green-400 border-green-500/30" :
              result.status === "drifted" ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" :
              "bg-red-500/20 text-red-400 border-red-500/30"
            }`}>
              {result.status}
            </span>
            <span className="text-xs text-slate-500">{result.dry_run ? "Dry run" : "Applied"}</span>
          </div>
          {result.resources_checked && result.resources_checked.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {result.resources_checked.map((r) => (
                <span key={r} className="text-xs px-2 py-1 bg-slate-800 rounded text-slate-400 font-mono">{r}</span>
              ))}
            </div>
          )}
          {result.drifts_found && (
            <pre className="mt-3 max-h-40 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-400">
              {JSON.stringify(result.drifts_found, null, 2)}
            </pre>
          )}
          {result.error_message && (
            <p className="text-sm text-red-400 mt-2">{result.error_message}</p>
          )}
        </div>
      )}
    </div>
  );
}
