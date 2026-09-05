/**
 * CodeGate — Interactive Pricing Section & Subscription Plans
 * Displays Community (Free), Team ($49/mo), Business ($199/mo), and Enterprise ($10K+/yr) tiers.
 */
import { useState } from "react";
import { Check, Zap, Building2, Users, Crown, ArrowRight, Sparkles } from "lucide-react";

interface PlanTier {
  id: string;
  name: string;
  badge: string;
  priceMonthly: string;
  priceAnnual: string;
  periodLabel: string;
  bestFor: string;
  description: string;
  popular?: boolean;
  accentColor: string;
  badgeBg: string;
  badgeBorder: string;
  badgeText: string;
  icon: React.ReactNode;
  features: string[];
  ctaLabel: string;
  ctaClass: string;
}

export default function PricingSection({ onSelectPlan }: { onSelectPlan?: (planId: string) => void }) {
  const [annual, setAnnual] = useState(true);

  const PLANS: PlanTier[] = [
    {
      id: "community",
      name: "Community",
      badge: "FREE FOREVER",
      priceMonthly: "$0",
      priceAnnual: "$0",
      periodLabel: "forever",
      bestFor: "Students, OSS & individual devs",
      description: "Core static analysis for independent developers and open-source projects.",
      accentColor: "#22c55e",
      badgeBg: "bg-emerald-500/10",
      badgeBorder: "border-emerald-500/30",
      badgeText: "text-emerald-400",
      icon: <Zap className="w-5 h-5 text-emerald-400" />,
      features: [
        "CLI + VS Code extension",
        "GitHub Action integration",
        "Unlimited static scans",
        "1 repository included",
        "Path-sensitive leak cards",
        "LibCST auto-fix generator",
        "Community Discord support",
      ],
      ctaLabel: "Get Started Free",
      ctaClass: "bg-[#161922] text-white hover:bg-[#202432] border border-[#2b3042]",
    },
    {
      id: "team",
      name: "Team",
      badge: "MOST POPULAR",
      popular: true,
      priceMonthly: "$49",
      priceAnnual: "$41",
      periodLabel: annual ? "billed $490/yr" : "per month",
      bestFor: "Small engineering teams",
      description: "Everything in Community plus team telemetry, PR checks, and user dashboard.",
      accentColor: "#007aff",
      badgeBg: "bg-[#007aff]/15",
      badgeBorder: "border-[#007aff]/40",
      badgeText: "text-[#007aff]",
      icon: <Users className="w-5 h-5 text-[#007aff]" />,
      features: [
        "Everything in Community",
        "Developer user panel",
        "Up to 10 private repos",
        "Team analytics dashboard",
        "Automated GitHub PR checks",
        "Scan history & telemetry",
        "Slack & Teams notifications",
        "Email support",
      ],
      ctaLabel: "Start 14-Day Trial",
      ctaClass: "bg-[#007aff] text-white hover:bg-[#0066d6] shadow-lg shadow-blue-600/30 font-semibold",
    },
    {
      id: "business",
      name: "Business",
      badge: "FOR GROWING TEAMS",
      priceMonthly: "$199",
      priceAnnual: "$165",
      periodLabel: annual ? "billed $1,990/yr" : "per month",
      bestFor: "Growing tech companies",
      description: "Admin organization portal, RBAC permissions, and centralized policy rules.",
      accentColor: "#a855f7",
      badgeBg: "bg-purple-500/15",
      badgeBorder: "border-purple-500/40",
      badgeText: "text-purple-300",
      icon: <Building2 className="w-5 h-5 text-purple-400" />,
      features: [
        "Everything in Team",
        "Admin Organization Panel",
        "Up to 50 private repos",
        "Role-Based Access (RBAC)",
        "Organization policy engine",
        "Centralized key management",
        "Advanced leak analytics",
        "Priority email & chat SLA",
      ],
      ctaLabel: "Upgrade to Business",
      ctaClass: "bg-purple-600 text-white hover:bg-purple-500 shadow-lg shadow-purple-600/30 font-semibold",
    },
    {
      id: "enterprise",
      name: "Enterprise",
      badge: "CUSTOM SECURITY",
      priceMonthly: "Custom",
      priceAnnual: "Custom",
      periodLabel: "starting ~$10K/year",
      bestFor: "Large organizations & regulated enterprise",
      description: "Self-hosted deployments, SAML/SSO, compliance reports, and 24/7 SLA.",
      accentColor: "#ef4444",
      badgeBg: "bg-red-500/15",
      badgeBorder: "border-red-500/40",
      badgeText: "text-red-400",
      icon: <Crown className="w-5 h-5 text-red-400" />,
      features: [
        "Everything in Business",
        "Unlimited repositories",
        "Single Sign-On (SSO / SAML)",
        "Audit logs & SOC2 reports",
        "Self-hosted / Air-gapped",
        "Multi-language scanner engine",
        "Custom rule development",
        "Dedicated Solutions Engineer & 24/7 SLA",
      ],
      ctaLabel: "Contact Enterprise Sales",
      ctaClass: "bg-gradient-to-r from-red-600 to-amber-600 text-white hover:opacity-95 shadow-lg shadow-red-600/30 font-semibold",
    },
  ];

  return (
    <section id="pricing" className="py-16 px-4 sm:px-6 bg-[#08090a] text-white font-sans relative overflow-hidden">
      {/* Section Header */}
      <div className="max-w-[1200px] mx-auto text-center space-y-3 mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-0.5 rounded-md bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 text-xs font-mono font-medium">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Transparent Developer Tiers</span>
        </div>

        <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight text-white">
          Simple plans that scale with your team.
        </h2>

        <p className="text-xs sm:text-sm text-zinc-400 max-w-xl mx-auto leading-relaxed">
          From individual open-source developers to large enterprise security leads. Catch leaks early and automate code fixes.
        </p>

        {/* Monthly / Annual Toggle */}
        <div className="flex items-center justify-center gap-3 pt-2">
          <span className={`text-xs font-medium ${!annual ? "text-white" : "text-zinc-400"}`}>
            Monthly Billing
          </span>
          <button
            onClick={() => setAnnual(!annual)}
            className="w-11 h-5 rounded-full bg-[#13161f] border border-white/[0.08] p-0.5 flex items-center transition-colors cursor-pointer"
            aria-label="Toggle Annual Billing"
          >
            <div
              className={`w-4 h-4 rounded-full bg-indigo-500 transition-transform ${
                annual ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
          <span className={`text-xs font-medium flex items-center gap-1.5 ${annual ? "text-white" : "text-zinc-400"}`}>
            <span>Annual Billing</span>
            <span className="px-2 py-0.2 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-[10px] font-mono font-bold">
              Save ~18%
            </span>
          </span>
        </div>
      </div>

      {/* 4 Cards Grid */}
      <div className="max-w-[1280px] mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 items-stretch">
        {PLANS.map((plan) => (
          <div
            key={plan.id}
            className={`rounded-md bg-[#0d0f14] border p-5 flex flex-col justify-between relative transition-all duration-150 shadow-sm ${
              plan.popular
                ? "border-indigo-500 ring-1 ring-indigo-500/30"
                : "border-white/[0.08] hover:border-white/[0.15]"
            }`}
          >
            {/* Top Info */}
            <div className="space-y-3.5">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded-md bg-[#13161f] border border-white/[0.06]">
                  {plan.icon}
                </div>
                <span className={`px-2 py-0.5 rounded border text-[10px] font-mono font-semibold tracking-wider ${plan.badgeBg} ${plan.badgeBorder} ${plan.badgeText}`}>
                  {plan.badge}
                </span>
              </div>

              <div>
                <h3 className="text-lg font-bold text-white">{plan.name}</h3>
                <p className="text-xs text-zinc-400 mt-0.5 min-h-[32px]">{plan.bestFor}</p>
              </div>

              {/* Price Display */}
              <div className="py-2 border-y border-white/[0.06]">
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-bold text-white font-mono tracking-tight">
                    {annual ? plan.priceAnnual : plan.priceMonthly}
                  </span>
                  {plan.priceMonthly !== "Custom" && (
                    <span className="text-xs text-zinc-400">/dev/month</span>
                  )}
                </div>
                <p className="text-[10px] font-mono text-zinc-500 mt-0.5">{plan.periodLabel}</p>
              </div>

              {/* Feature List */}
              <div className="space-y-2 pt-1">
                <p className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold">
                  INCLUDED FEATURES:
                </p>
                <ul className="space-y-1.5">
                  {plan.features.map((feat, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-zinc-300">
                      <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Action CTA */}
            <div className="pt-5">
              <button
                onClick={() => onSelectPlan?.(plan.id)}
                className={`w-full py-2 px-3 rounded-md text-xs font-medium transition-all flex items-center justify-center gap-2 cursor-pointer ${plan.ctaClass}`}
              >
                <span>{plan.ctaLabel}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
