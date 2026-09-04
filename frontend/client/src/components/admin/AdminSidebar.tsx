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
    <aside className="w-64 bg-[#0c0d12] border-r border-[#1a1d29] flex flex-col justify-between shrink-0 min-h-screen text-zinc-300 font-poppins selection:bg-purple-500/30">
      <div className="p-5 space-y-6">
        {/* Brand Logo */}
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-rose-500 via-purple-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-rose-600/30 group-hover:scale-105 transition-transform">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-base font-bold text-white tracking-tight block font-poppins">
                LeakGuard
              </span>
              <span className="text-[10px] font-mono text-purple-400 block tracking-widest uppercase -mt-0.5">
                Admin Console
              </span>
            </div>
          </Link>

          <Link
            to="/dashboard"
            className="p-1.5 rounded-lg bg-[#141620] border border-[#222738] hover:border-purple-500/40 text-zinc-400 hover:text-white transition-all"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Global Search Quick Link */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Quick search..."
            onClick={() => setActiveTab("findings")}
            className="w-full bg-[#12141c] border border-[#202536] focus:border-rose-500 text-white placeholder-zinc-500 pl-8 pr-3 py-1.5 rounded-xl text-xs font-mono outline-none transition-colors cursor-pointer"
            readOnly
          />
        </div>

        {/* Navigation Menu */}
        <div className="space-y-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 px-3 block mb-2">
            Navigation
          </span>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return item.path ? (
              <Link
                key={item.id}
                to={item.path}
                className="flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium text-zinc-400 hover:text-white hover:bg-[#141622] transition-colors group"
              >
                <div className="flex items-center space-x-2.5">
                  <Icon className="w-4 h-4 text-zinc-500 group-hover:text-rose-400 transition-colors" />
                  <span>{item.label}</span>
                </div>
                <ExternalLink className="w-3 h-3 text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity" />
              </Link>
            ) : (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-2.5 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? "bg-gradient-to-r from-rose-500/20 to-purple-500/20 border border-rose-500/40 text-white font-semibold shadow-md shadow-rose-950/30"
                    : "text-zinc-400 hover:text-white hover:bg-[#141622] border border-transparent"
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                    isActive ? "text-rose-400" : "text-zinc-500"
                  }`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* System Health Status */}
        <div className="space-y-2 pt-2 border-t border-[#181b26]">
          <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 px-3 block">
            System Status
          </span>

          <div className="bg-[#12141c] border border-[#1e2333] rounded-xl p-3 space-y-2 text-[11px] font-mono">
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
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                <span>API Rate Limit</span>
              </span>
              <span className="text-purple-300 font-semibold">
                {rateRemaining !== null ? `${rateRemaining}/${rateLimit || 60}` : "60/60"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* User Footer Profile & Token Access Button */}
      <div className="p-4 border-t border-[#181b26] bg-[#090a0e] space-y-3">
        <button
          onClick={onOpenTokenModal}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-[#13151f] hover:bg-[#1a1d2c] border border-[#23283b] hover:border-amber-500/40 text-xs font-mono transition-colors"
        >
          <span className="flex items-center space-x-2 text-zinc-300">
            <KeyRound className="w-3.5 h-3.5 text-amber-400" />
            <span>{tokenPresent ? "PAT Token Saved" : "Set GitHub Token"}</span>
          </span>
          <span className={`w-2 h-2 rounded-full ${tokenPresent ? "bg-emerald-400" : "bg-amber-400 animate-pulse"}`} />
        </button>

        {currentUser && (
          <div className="flex items-center space-x-3 px-1 pt-1">
            <img
              src={currentUser.avatar_url || "https://avatars.githubusercontent.com/u/9919?v=4"}
              alt={currentUser.login}
              className="w-8 h-8 rounded-full border border-purple-500/40 object-cover"
            />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-white truncate font-poppins">
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
