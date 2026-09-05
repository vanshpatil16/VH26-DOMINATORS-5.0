/** Small presentation helpers shared by the admin panel components. */

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";

  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 45) return "just now";
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

/** Tailwind classes for a check/workflow conclusion pill. */
export function conclusionStyle(status: string, conclusion: string | null): string {
  if (status !== "completed") return "bg-sky-500/10 border-sky-500/30 text-sky-300";
  switch (conclusion) {
    case "success":
      return "bg-emerald-500/10 border-emerald-500/30 text-emerald-300";
    case "failure":
      return "bg-rose-500/10 border-rose-500/30 text-rose-300";
    case "cancelled":
    case "skipped":
      return "bg-zinc-500/10 border-zinc-600/40 text-zinc-400";
    case "timed_out":
    case "action_required":
      return "bg-amber-500/10 border-amber-500/30 text-amber-300";
    default:
      return "bg-zinc-500/10 border-zinc-600/40 text-zinc-400";
  }
}

export function conclusionLabel(status: string, conclusion: string | null): string {
  if (status !== "completed") return status.replace("_", " ");
  return conclusion ?? "unknown";
}

/** Tailwind classes for a finding severity chip. */
export function levelStyle(level: "error" | "warning" | "notice"): string {
  switch (level) {
    case "error":
      return "bg-rose-500/10 border-rose-500/30 text-rose-300";
    case "warning":
      return "bg-amber-500/10 border-amber-500/30 text-amber-300";
    default:
      return "bg-sky-500/10 border-sky-500/30 text-sky-300";
  }
}

export function eventLabel(event: string, prNumbers: number[]): string {
  if (event === "pull_request") return prNumbers.length ? `PR #${prNumbers[0]}` : "pull request";
  if (event === "scan") return "on-demand scan";
  return event.replace("_", " ");
}
