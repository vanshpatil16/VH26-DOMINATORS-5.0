import React from "react";
import { Link, useLocation } from "wouter";
import {
  LayoutDashboard,
  GitBranch,
  AlertTriangle,
  Users,
  ShieldCheck,
  Code2,
  Settings,
  ArrowLeft,
  Search,
  ExternalLink,
  Sparkles,
  DatabaseZap,
  KeyRound,
  FileCode2,
} from "lucide-react";
import type { GitHubUser } from "@/lib/github";

interface AdminSidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  currentUser: GitHubUser | null;
  dbConnected: boolean;
  rateRemaining: number | null;
  rateLimit: number | null;
  tokenPresent: boolean;
  onOpenTokenModal: () => void;
}

export default function AdminSidebar({
  activeTab,
  setActiveTab,
  currentUser,
  dbConnected,
  rateRemaining,
  rateLimit,
  tokenPresent,
  onOpenTokenModal,
}: AdminSidebarProps) {
  const [, setLocation] = useLocation();

  const navItems = [
    { id: "overview", label: "Dashboard", icon: LayoutDashboard },
    { id: "branches", label: "Branches & Commits", icon: GitBranch },
    { id: "findings", label: "Leak Findings", icon: AlertTriangle },
    { id: "accounts", label: "Connected Accounts", icon: Users },
    { id: "codegate", label: "CodeGate Scanner", icon: Code2, path: "/codegate" },
    { id: "graph", label: "AST Code Graph", icon: FileCode2, path: "/graph" },
  ];

  return (
    <aside className="w-60 bg-[#0d0f14] border-r border-white/[0.06] flex flex-col justify-between shrink-0 min-h-screen text-zinc-300 font-sans selection:bg-indigo-500/30">
      <div className="p-4 space-y-4">
        {/* Brand Logo */}
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2.5 group">
            <div className="w-8 h-8 rounded-md bg-indigo-600 flex items-center justify-center shadow-sm group-hover:bg-indigo-500 transition-colors">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            <div>
              <span className="text-sm font-bold text-white tracking-tight block">
                LeakGuard
              </span>
              <span className="text-[9px] font-mono text-indigo-400 block tracking-wider uppercase">
                Admin Console
              </span>
            </div>
          </Link>

          <Link
            to="/dashboard"
            className="p-1 rounded-md bg-[#13161f] border border-white/[0.08] hover:border-indigo-500/40 text-zinc-400 hover:text-white transition-all"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Global Search Quick Link */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Quick search..."
            onClick={() => setActiveTab("findings")}
            className="w-full bg-[#13161f] border border-white/[0.08] focus:border-indigo-500 text-white placeholder-zinc-500 pl-8 pr-3 py-1 rounded-md text-xs font-mono outline-none transition-colors cursor-pointer"
            readOnly
          />
        </div>

        {/* Navigation Menu */}
        <div className="space-y-0.5">
          <span className="text-[9px] font-mono uppercase tracking-wider text-zinc-400 px-2 block mb-1 font-semibold">
            Navigation
          </span>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            if (item.path) {
              return (
                <button
                  key={item.id}
                  onClick={() => setLocation(item.path!)}
                  className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs font-medium text-zinc-400 hover:text-white hover:bg-white/5 transition-all text-left group"
                >
                  <div className="flex items-center space-x-2">
                    <Icon className="w-3.5 h-3.5 text-zinc-500 group-hover:text-indigo-400 transition-colors" />
                    <span>{item.label}</span>
                  </div>
                  <ExternalLink className="w-3 h-3 text-zinc-600 group-hover:text-zinc-400" />
                </button>
              );
            }

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-2 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all text-left ${
                  isActive
                    ? "bg-indigo-600/20 text-indigo-200 border border-indigo-500/30 font-semibold"
                    : "text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-indigo-400" : "text-zinc-500"}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* System Health Status */}
        <div className="space-y-1.5 pt-3 border-t border-white/[0.06]">
          <span className="text-[9px] font-mono uppercase tracking-wider text-zinc-400 px-2 block font-semibold">
            System Status
          </span>

          <div className="bg-[#13161f] border border-white/[0.06] rounded-md p-2.5 space-y-1.5 text-[11px] font-mono">
            <div className="flex items-center justify-between">
              <span className="text-zinc-400 flex items-center space-x-1.5">
                <DatabaseZap className={`w-3.5 h-3.5 ${dbConnected ? "text-emerald-400" : "text-rose-400"}`} />
                <span>MongoDB DB</span>
              </span>
              <span className={dbConnected ? "text-emerald-400 font-semibold" : "text-rose-400"}>
                {dbConnected ? "Connected" : "Offline"}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-zinc-400 flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span>API Rate Limit</span>
              </span>
              <span className="text-indigo-300 font-semibold">
                {rateRemaining !== null ? `${rateRemaining}/${rateLimit || 60}` : "60/60"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* User Footer Profile & Token Access Button */}
      <div className="p-3 border-t border-white/[0.06] bg-[#08090a] space-y-2">
        <button
          onClick={onOpenTokenModal}
          className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md bg-[#13161f] hover:bg-white/10 border border-white/[0.08] text-xs font-mono transition-colors"
        >
          <span className="flex items-center space-x-1.5 text-zinc-300">
            <KeyRound className="w-3.5 h-3.5 text-amber-400" />
            <span>{tokenPresent ? "PAT Token Saved" : "Set GitHub Token"}</span>
          </span>
          <span className={`w-2 h-2 rounded-full ${tokenPresent ? "bg-emerald-400" : "bg-amber-400 animate-pulse"}`} />
        </button>

        {currentUser && (
          <div className="flex items-center space-x-2.5 px-1 pt-1">
            <img
              src={currentUser.avatar_url || "https://avatars.githubusercontent.com/u/9919?v=4"}
              alt={currentUser.login}
              className="w-7 h-7 rounded-full border border-indigo-500/30 object-cover"
            />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-white truncate">
                {currentUser.name || currentUser.login}
              </p>
              <p className="text-[10px] font-mono text-zinc-400 truncate">
                @{currentUser.login}
              </p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
