import React from "react";
import { Link } from "wouter";
import { ArrowLeft, GitBranch, Sparkles } from "lucide-react";
import AstGraphVisualizer from "../components/AstGraphVisualizer";

export default function Graph() {
  return (
    <div className="min-h-screen bg-[#07080a] text-zinc-100 font-poppins selection:bg-purple-500/30 selection:text-purple-200 p-4 md:p-8 space-y-6">
      {/* Navigation & Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1c1f28]">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#0d0e12] border border-[#1c1f28] hover:border-purple-500/50 hover:bg-[#13151c] text-zinc-400 hover:text-white transition-all duration-200 text-xs font-medium group shadow-sm shadow-black/40"
          >
            <ArrowLeft className="w-4 h-4 text-zinc-400 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to Dashboard</span>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl md:text-2xl font-semibold text-white tracking-tight flex items-center gap-2">
                AST & Code Graph Visualizer
              </h1>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400 text-[10px] font-medium tracking-wide">
                <Sparkles className="w-3 h-3" /> Dynamic Canvas
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              Interactive node & edge flow for Abstract Syntax Search Tree navigation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#0d0e12] border border-[#1c1f28] text-xs text-zinc-400">
            <GitBranch className="w-3.5 h-3.5 text-purple-400" />
            <span>Interactive Drag & Marching-Ant Flow</span>
          </div>
        </div>
      </header>

      {/* Main AST Graph Visualizer Canvas */}
      <main className="w-full">
        <AstGraphVisualizer />
      </main>
    </div>
  );
}
