"use client";

import { useEffect, useState } from "react";
import { Key, Plus, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface ApiKey {
  id: string;
  provider: string;
  key_name: string;
  created_at: string;
}

export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.projects.list().then(() => {
      // Stub — API keys endpoint to be wired
      setKeys([]);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">API Keys</h1>
          <p className="text-slate-400 mt-1">Manage provider credentials for your projects</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors">
          <Plus className="h-4 w-4" />
          Add Key
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        </div>
      ) : keys.length === 0 ? (
        <div className="text-center py-20">
          <Key className="h-16 w-16 mx-auto text-slate-600 mb-4" />
          <h2 className="text-xl font-semibold text-slate-300 mb-2">No API keys</h2>
          <p className="text-slate-500">Add GitHub, Vercel, or Fly.io credentials to enable deployments</p>
        </div>
      ) : (
        <div className="space-y-3">
          {keys.map((key) => (
            <div key={key.id} className="flex items-center justify-between p-4 bg-slate-900 border border-slate-800 rounded-lg">
              <div>
                <p className="font-medium text-white">{key.key_name}</p>
                <p className="text-sm text-slate-500">{key.provider} · {formatDate(key.created_at)}</p>
              </div>
              <button className="p-2 text-slate-500 hover:text-red-400 transition-colors">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
