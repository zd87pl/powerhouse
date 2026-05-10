"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Loader2, Box } from "lucide-react";
import { api, type Project } from "@/lib/api";
import { errorMessage, formatDate, statusColor } from "@/lib/utils";
import { CreateProjectDialog } from "@/components/create-project-dialog";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.projects.list();
      setProjects(data.projects);
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(fetchProjects);
  }, [fetchProjects]);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Projects</h1>
          <p className="text-slate-400 mt-1">Manage your autonomous engineering projects</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Project
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
          {error}
          <button onClick={fetchProjects} className="ml-2 underline">Retry</button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        </div>
      )}

      {/* Empty state */}
      {!loading && projects.length === 0 && (
        <div className="text-center py-20">
          <Box className="h-16 w-16 mx-auto text-slate-600 mb-4" />
          <h2 className="text-xl font-semibold text-slate-300 mb-2">No projects yet</h2>
          <p className="text-slate-500 mb-6">Create your first project to get started</p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Project
          </button>
        </div>
      )}

      {/* Project grid */}
      {!loading && projects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/dashboard/projects/${project.id}`}
              className="block p-6 bg-slate-900 border border-slate-800 rounded-xl hover:border-indigo-500/30 hover:bg-slate-800/50 transition-all group"
            >
              <div className="flex items-start justify-between mb-4">
                <h3 className="font-semibold text-white group-hover:text-indigo-400 transition-colors">
                  {project.name}
                </h3>
                <span className={`text-xs px-2 py-1 rounded-full border ${statusColor(project.status)}`}>
                  {project.status}
                </span>
              </div>
              {project.description && (
                <p className="text-sm text-slate-400 mb-4 line-clamp-2">{project.description}</p>
              )}
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 uppercase tracking-wider">{project.stack}</span>
                <span className="text-xs text-slate-500">{formatDate(project.updated_at)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create dialog */}
      <CreateProjectDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={(project) => {
          setProjects([project, ...projects]);
          setShowCreate(false);
        }}
      />
    </div>
  );
}
