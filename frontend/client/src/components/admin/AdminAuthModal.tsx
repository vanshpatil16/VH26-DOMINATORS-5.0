import React, { useState } from "react";
import { ShieldAlert, Lock, User, KeyRound, ArrowLeft } from "lucide-react";
import { Link } from "wouter";

interface Props {
  onAuthenticated: () => void;
}

export default function AdminAuthModal({ onAuthenticated }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username.trim() === "admin" && password === "admin") {
      sessionStorage.setItem("admin_authenticated", "true");
      setError("");
      onAuthenticated();
    } else {
      setError("Invalid username or password. Please try again.");
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/85 backdrop-blur-md font-poppins">
      <div className="relative w-full max-w-md rounded-2xl bg-[#09090d] border border-[#1e2130] p-7 shadow-2xl shadow-black/80">
        
        {/* Header */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-center mb-3">
            <Lock className="w-6 h-6 text-rose-400" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Admin Authentication</h2>
          <p className="text-xs text-zinc-400 mt-1">Enter your credentials to access the CodeGate Admin Dashboard</p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 px-3.5 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-300 text-xs font-mono flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[11px] font-mono text-zinc-400 uppercase mb-1.5">Username</label>
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                autoFocus
                required
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#0d0e17] border border-[#1e2130] text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-rose-500/50 focus:ring-1 focus:ring-rose-500/50 transition-all font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-zinc-400 uppercase mb-1.5">Password</label>
            <div className="relative">
              <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#0d0e17] border border-[#1e2130] text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-rose-500/50 focus:ring-1 focus:ring-rose-500/50 transition-all font-mono"
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full mt-2 py-3 px-4 rounded-xl text-xs font-semibold uppercase tracking-wider text-white bg-gradient-to-r from-rose-500 to-purple-600 hover:from-rose-600 hover:to-purple-700 shadow-lg shadow-rose-500/20 active:scale-[0.98] transition-all"
          >
            Authenticate
          </button>
        </form>

        {/* Back Link */}
        <div className="mt-5 pt-4 border-t border-[#181b26] flex items-center justify-center">
          <Link
            href="/dashboard"
            className="text-xs font-mono text-zinc-500 hover:text-zinc-300 flex items-center gap-1.5 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
