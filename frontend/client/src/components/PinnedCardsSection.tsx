import React, { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, Sparkles, Zap, Shield, Layers, Cpu } from "lucide-react";

const pinnedCards = [
  {
    id: "01",
    kicker: "01 / INTAKE & TRIAGE",
    title: "Automated Issue Ingestion",
    description: "Convert Slack messages, GitHub discussions, and customer tickets into structured Linear issues instantly.",
    stat: "99.8% Sync Accuracy",
    statSub: "Zero Context Switching",
    icon: Layers,
    accent: "bg-gradient-to-br from-cyan-900/70 via-blue-900/60 to-slate-950",
    borderAccent: "border-cyan-400/70 hover:border-cyan-300 shadow-[0_0_45px_rgba(6,182,212,0.3)]",
    badgeBg: "bg-cyan-500/25 border-cyan-400/50 text-cyan-200",
    textAccent: "text-cyan-300",
    buttonBg: "bg-cyan-400 text-black hover:bg-cyan-300",
  },
  {
    id: "02",
    kicker: "02 / AI WORKFLOWS",
    title: "Autonomous Agent Dispatch",
    description: "Linear Agents analyze PRDs, write pull requests, and review code diffs continuously in the background.",
    stat: "3.4x Faster Cycle",
    statSub: "24/7 Autonomy",
    icon: Sparkles,
    accent: "bg-gradient-to-br from-fuchsia-900/70 via-purple-900/60 to-slate-950",
    borderAccent: "border-fuchsia-400/70 hover:border-fuchsia-300 shadow-[0_0_45px_rgba(217,70,239,0.3)]",
    badgeBg: "bg-fuchsia-500/25 border-fuchsia-400/50 text-fuchsia-200",
    textAccent: "text-fuchsia-300",
    buttonBg: "bg-fuchsia-400 text-black hover:bg-fuchsia-300",
  },
  {
    id: "03",
    kicker: "03 / HIGH VELOCITY",
    title: "Keyboard-First Architecture",
    description: "Navigate, create, and update issues instantly with built-in command palette and sub-50ms latency.",
    stat: "<50ms Response",
    statSub: "100% Keyboard Driven",
    icon: Zap,
    accent: "bg-gradient-to-br from-amber-900/70 via-orange-900/60 to-slate-950",
    borderAccent: "border-amber-400/70 hover:border-amber-300 shadow-[0_0_45px_rgba(245,158,11,0.3)]",
    badgeBg: "bg-amber-500/25 border-amber-400/50 text-amber-200",
    textAccent: "text-amber-300",
    buttonBg: "bg-amber-400 text-black hover:bg-amber-300",
  },
  {
    id: "04",
    kicker: "04 / STRATEGY",
    title: "Real-Time Progress Engine",
    description: "Track velocity across cycles, monitor team bandwidth, and spot blockers before deadlines slip.",
    stat: "Live Telemetry",
    statSub: "Dynamic Forecasts",
    icon: Cpu,
    accent: "bg-gradient-to-br from-emerald-900/70 via-teal-900/60 to-slate-950",
    borderAccent: "border-emerald-400/70 hover:border-emerald-300 shadow-[0_0_45px_rgba(16,185,129,0.3)]",
    badgeBg: "bg-emerald-500/25 border-emerald-400/50 text-emerald-200",
    textAccent: "text-emerald-300",
    buttonBg: "bg-emerald-400 text-black hover:bg-emerald-300",
  },
  {
    id: "05",
    kicker: "05 / ENTERPRISE",
    title: "Bank-Grade Security & Audit",
    description: "SOC2 Type II certified, SAML SSO, granular access controls, and encrypted workspace data.",
    stat: "99.99% Uptime",
    statSub: "SOC2 Type II",
    icon: Shield,
    accent: "bg-gradient-to-br from-indigo-900/70 via-blue-950/60 to-slate-950",
    borderAccent: "border-indigo-400/70 hover:border-indigo-300 shadow-[0_0_45px_rgba(99,102,241,0.3)]",
    badgeBg: "bg-indigo-500/25 border-indigo-400/50 text-indigo-200",
    textAccent: "text-indigo-300",
    buttonBg: "bg-indigo-400 text-black hover:bg-indigo-300",
  },
];

export default function PinnedCardsSection() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  // Precise scroll keyframes for pinning:
  // [0 -> 0.08]: Viewport locks in place, header fades in.
  // [0.08 -> 0.88]: Cards translate smoothly from Right to Left.
  // [0.88 -> 1.0]: Screen stays pinned on final card before unsticking down the page.
  const x = useTransform(
    scrollYProgress,
    [0, 0.08, 0.88, 1],
    ["0%", "0%", "-75%", "-75%"]
  );

  const progressBarWidth = useTransform(
    scrollYProgress,
    [0.08, 0.88],
    ["0%", "100%"]
  );

  return (
    <section ref={containerRef} className="relative h-[380vh] bg-[#08090a]">
      {/* Sticky Viewport - Pinning the screen solid while user scrolls */}
      <div className="sticky top-0 h-screen overflow-hidden flex flex-col justify-center border-t border-b border-[#1f2226] py-10 z-10">
        {/* Header */}
        <div className="max-w-6xl mx-auto w-full px-6 mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="text-[10px] font-mono tracking-widest text-zinc-400 uppercase block mb-2">
              PINNED CAPABILITY SHOWCASE
            </span>
            <h2 className="text-3xl md:text-5xl font-medium text-white tracking-tight">
              Designed for speed. <br className="hidden md:block" />
              <span className="text-zinc-400">Built for precision.</span>
            </h2>
          </div>

          <div className="flex items-center space-x-3 text-xs font-mono text-zinc-300 bg-white/10 border border-white/20 px-4 py-2 rounded-full w-fit backdrop-blur-md">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>SCROLL DOWN TO GLIDE CARDS</span>
          </div>
        </div>

        {/* Horizontal Motion Track */}
        <div className="w-full overflow-hidden pl-6 md:pl-20">
          <motion.div style={{ x }} className="flex space-x-6 md:space-x-8 w-max">
            {pinnedCards.map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.id}
                  className={`w-[320px] md:w-[460px] h-[360px] md:h-[420px] rounded-2xl ${card.accent} border ${card.borderAccent} p-6 md:p-8 flex flex-col justify-between relative group transition-all duration-300 shadow-2xl backdrop-blur-md`}
                >
                  {/* Top card info */}
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <span className={`text-xs font-mono tracking-widest ${card.textAccent} font-semibold`}>
                        {card.kicker}
                      </span>
                      <div className={`p-2.5 rounded-xl border ${card.badgeBg} group-hover:scale-110 transition-transform`}>
                        <Icon className="w-5 h-5" />
                      </div>
                    </div>

                    <h3 className="text-2xl md:text-3xl font-semibold text-white mb-3 tracking-tight">
                      {card.title}
                    </h3>
                    <p className="text-zinc-200 text-sm md:text-base leading-relaxed font-normal">
                      {card.description}
                    </p>
                  </div>

                  {/* Bottom Stats & Visual */}
                  <div className="pt-6 border-t border-white/20 flex items-center justify-between">
                    <div>
                      <div className={`text-xl md:text-2xl font-mono font-bold tracking-tight ${card.textAccent}`}>
                        {card.stat}
                      </div>
                      <div className="text-xs font-mono text-zinc-300 font-medium">
                        {card.statSub}
                      </div>
                    </div>

                    <div className={`w-11 h-11 rounded-full ${card.buttonBg} flex items-center justify-center font-bold transition-transform group-hover:scale-110 shadow-lg`}>
                      <ArrowRight className="w-5 h-5" />
                    </div>
                  </div>
                </div>
              );
            })}
          </motion.div>
        </div>

        {/* Pin Progress Indicator Bar at Bottom of Viewport */}
        <div className="max-w-6xl mx-auto w-full px-6 mt-8 flex items-center justify-between">
          <div className="text-xs font-mono text-zinc-400 uppercase tracking-wider font-medium">
            CARD PROGRESS
          </div>
          <div className="w-48 md:w-64 h-2 bg-white/10 rounded-full overflow-hidden border border-white/10">
            <motion.div
              style={{ width: progressBarWidth }}
              className="h-full bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-emerald-400 rounded-full"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
