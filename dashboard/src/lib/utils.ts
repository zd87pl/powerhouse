import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function statusColor(status: string): string {
  switch (status) {
    case "valid": return "bg-green-500/20 text-green-400 border-green-500/30"
    case "passed": return "bg-green-500/20 text-green-400 border-green-500/30"
    case "synced": return "bg-green-500/20 text-green-400 border-green-500/30"
    case "succeeded": return "bg-green-500/20 text-green-400 border-green-500/30"
    case "connected": return "bg-green-500/20 text-green-400 border-green-500/30"
    case "warning": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
    case "drifted": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
    case "action_required": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
    case "configured": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
    case "invalid": return "bg-red-500/20 text-red-400 border-red-500/30"
    case "error": return "bg-red-500/20 text-red-400 border-red-500/30"
    case "failed": return "bg-red-500/20 text-red-400 border-red-500/30"
    case "missing": return "bg-red-500/20 text-red-400 border-red-500/30"
    case "reconciling": return "bg-blue-500/20 text-blue-400 border-blue-500/30"
    case "running": return "bg-blue-500/20 text-blue-400 border-blue-500/30"
    case "pending": return "bg-slate-500/20 text-slate-400 border-slate-500/30"
    case "queued": return "bg-slate-500/20 text-slate-400 border-slate-500/30"
    case "skipped": return "bg-slate-500/20 text-slate-400 border-slate-500/30"
    default: return "bg-slate-500/20 text-slate-400 border-slate-500/30"
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}
