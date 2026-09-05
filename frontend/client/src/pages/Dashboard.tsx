import React, { useState, useEffect } from "react";
import { Link, useLocation } from "wouter";
import {
  Search,
  Mic,
  FileBarChart2,
  Calendar,
  ChevronDown,
  ArrowUpRight,
  TrendingUp,
  TrendingDown,
  Sparkles,
  AlertTriangle,
  Bot,
  Grid as GridIcon,
  FileText,
  Sliders,
  Lightbulb,
  X,
  User,
  ArrowLeft,
  Github,
  GitBranch,
  GitCommit,
  FolderGit2,
  ExternalLink,
  RefreshCw,
  Code2,
  Clock,
  CheckCircle2,
  LogOut,
  Copy,
  Network,
  ShieldCheck,
  CreditCard,
} from "lucide-react";
import PricingSection from "../components/PricingSection";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { toast } from "sonner";
import AuthModal from "../components/AuthModal";
import LeakReportModal from "../components/LeakReportModal";
import {
  fetchGitHubUser,
  fetchUserRepos,
  fetchRepoCommits,
  processCommitTimeline,
  GitHubRepo,
  GitHubCommit,
  GitHubUser,
} from "../lib/github";

const defaultChartData = [
  { day: "1", users: 70 },
  { day: "3", users: 100 },
  { day: "5", users: 70 },
  { day: "7", users: 30 },
  { day: "9", users: 30 },
  { day: "11", users: 101 },
  { day: "13", users: 125 },
  { day: "15", users: 125 },
  { day: "17", users: 160 },
  { day: "19", users: 200 },
  { day: "21", users: 200 },
  { day: "23", users: 140 },
  { day: "25", users: 110 },
  { day: "27", users: 130 },
  { day: "29", users: 160 },
  { day: "31", users: 130 },
];

const times = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"];
const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/**
 * Computes a 6x7 activity matrix (6 time slots x 7 days) and time distribution percentages
 * from real GitHub API commit timestamps.
 */
function buildHeatmapFromCommits(commits: GitHubCommit[]) {
  // 6 time blocks (4h each: 0-3, 4-7, 8-11, 12-15, 16-19, 20-23) x 7 days (0=Sun..6=Sat)
  const grid: number[][] = Array.from({ length: 6 }, () => Array(7).fill(0));
  let nightCount = 0;   // 00:00 - 07:59
  let morningCount = 0; // 08:00 - 15:59
  let eveningCount = 0; // 16:00 - 23:59

  if (!commits || commits.length === 0) {
    return {
      grid: [
        [0, 1, 0, 1, 1, 0, 0],
        [0, 0, 1, 0, 1, 1, 0],
        [1, 2, 2, 2, 1, 2, 1],
        [2, 3, 2, 3, 3, 2, 1],
        [1, 2, 1, 2, 2, 2, 0],
        [1, 1, 2, 1, 1, 1, 0],
      ],
      maxCount: 3,
      nightPct: 15,
      morningPct: 55,
      dayPct: 30,
      eveningPct: 15,
      totalCommits: 0,
      peakSlotLabel: "12:00–16:00",
    };
  }

  let maxCount = 0;
  commits.forEach((c) => {
    const d = new Date(c.date);
    const day = d.getDay(); // 0=Sun..6=Sat
    const hour = d.getHours(); // 0..23

    const slot = Math.floor(hour / 4); // 0..5
    grid[slot][day] += 1;
    if (grid[slot][day] > maxCount) maxCount = grid[slot][day];

    if (hour >= 0 && hour < 8) nightCount++;
    else if (hour >= 8 && hour < 16) morningCount++;
    else eveningCount++;
  });

  const total = commits.length || 1;
  const nightPct = Math.round((nightCount / total) * 100);
  const morningPct = Math.round((morningCount / total) * 100);
  const dayPct = Math.max(0, 100 - nightPct - morningPct);

  // Find peak time slot
  let peakSlot = 3;
  let peakVal = -1;
  grid.forEach((row, sIdx) => {
    const sum = row.reduce((a, b) => a + b, 0);
    if (sum > peakVal) {
      peakVal = sum;
      peakSlot = sIdx;
    }
  });

  const slotLabels = [
    "00:00–04:00 (Night)",
    "04:00–08:00 (Early Morning)",
    "08:00–12:00 (Morning)",
    "12:00–16:00 (Afternoon)",
    "16:00–20:00 (Evening)",
    "20:00–24:00 (Late Night)",
  ];

  return {
    grid,
    maxCount,
    nightPct,
    morningPct,
    dayPct,
    eveningPct: dayPct,
    totalCommits: commits.length,
    peakSlotLabel: slotLabels[peakSlot] || "Morning",
  };
}

export default function Dashboard() {
  const [, navigate] = useLocation();
  const [activeTab, setActiveTab] = useState("Overview");
  const [githubUsername, setGithubUsername] = useState("");
  const [githubUser, setGithubUser] = useState<GitHubUser | null>(null);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [commits, setCommits] = useState<GitHubCommit[]>([]);
  const [loading, setLoading] = useState(false);
  const [repoDropdownOpen, setRepoDropdownOpen] = useState(false);
  const [searchCommitQuery, setSearchCommitQuery] = useState("");
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem("connected_github_user");
    localStorage.removeItem("github_token");
    setGithubUsername("");
    setGithubUser(null);
    setRepos([]);
    setCommits([]);
    toast.success("Logged out successfully");
    setIsAuthModalOpen(true);
  };

  useEffect(() => {
    const savedUser = localStorage.getItem("connected_github_user");
    if (savedUser) {
      setGithubUsername(savedUser);
      loadDashboardGitHubData(savedUser);
    } else {
      setIsAuthModalOpen(true);
    }
  }, []);

  const loadDashboardGitHubData = async (username: string) => {
    setLoading(true);
    const userInfo = await fetchGitHubUser(username);
    const userRepos = await fetchUserRepos(username);

    if (userInfo) setGithubUser(userInfo);
    if (userRepos.length > 0) {
      setRepos(userRepos);
      const targetRepo = userRepos[0]?.name || "Omkars-Portfolio";
      setSelectedRepo(targetRepo);
      const topCommits = await fetchRepoCommits(username, targetRepo);
      setCommits(topCommits);
    }
    setLoading(false);
  };

  const handleSelectRepo = async (repoName: string) => {
    setSelectedRepo(repoName);
    setRepoDropdownOpen(false);
    setLoading(true);
    const repoCommits = await fetchRepoCommits(githubUsername, repoName);
    setCommits(repoCommits);
    setLoading(false);
  };

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    toast.success(`Copied commit SHA: ${sha}`);
  };

  // Filtered commits based on search
  const filteredCommits = commits.filter(
    (c) =>
      c.message.toLowerCase().includes(searchCommitQuery.toLowerCase()) ||
      c.sha.toLowerCase().includes(searchCommitQuery.toLowerCase()) ||
      c.authorName.toLowerCase().includes(searchCommitQuery.toLowerCase())
  );

  // Language breakdown from GitHub API
  const languageCounts: { [key: string]: number } = {};
  repos.forEach((r) => {
    const lang = r.language || "Other";
    languageCounts[lang] = (languageCounts[lang] || 0) + 1;
  });
  const totalLangs = repos.length || 1;
  const langBreakdown = Object.entries(languageCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count]) => ({
      name,
      percentage: Math.round((count / totalLangs) * 100),
    }));

  return (
    <div className="font-sans min-h-screen bg-[#08090a] text-white p-4 md:p-6 select-none">
      {/* Outer Card Wrapper */}
      <div className="max-w-[1440px] mx-auto bg-[#0d0f14] border border-white/[0.08] rounded-xl p-4 md:p-6 shadow-xl space-y-5">

        {/* Top Navbar */}
        <header className="flex flex-wrap xl:flex-nowrap items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
          {/* Brand Logo & Back to Home */}
          <div className="flex items-center space-x-3 shrink-0">
            <Link
              to="/"
              className="p-1.5 rounded-md bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors shrink-0"
              title="Back to Landing Page"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h1 className="text-lg md:text-xl font-bold tracking-tight text-white flex items-center space-x-2 shrink-0">
              <span>Insighta</span>
              <span className="text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/25 px-2 py-0.5 rounded-md font-mono font-normal whitespace-nowrap">
                GitHub AI
              </span>
            </h1>
          </div>

          {/* Navigation Pill Tabs */}
          <div className="flex items-center bg-[#13161f] border border-white/[0.06] p-1 rounded-md overflow-x-auto shrink-0 max-w-full custom-scrollbar gap-1">
            <button
              onClick={() => setActiveTab("Overview")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activeTab === "Overview"
                ? "bg-indigo-600 text-white font-semibold shadow-sm"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
                }`}
            >
              <GridIcon className="w-3.5 h-3.5" />
              <span>Overview</span>
            </button>
            <button
              onClick={() => setActiveTab("Reports")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activeTab === "Reports"
                ? "bg-indigo-600 text-white font-semibold shadow-sm"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
                }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Reports</span>
            </button>
            <button
              onClick={() => setActiveTab("Optimization")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activeTab === "Optimization"
                ? "bg-indigo-600 text-white font-semibold shadow-sm"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
                }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>Optimization</span>
            </button>
            <button
              onClick={() => setActiveTab("Insights")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activeTab === "Insights"
                ? "bg-indigo-600 text-white font-semibold shadow-sm"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
                }`}
            >
              <Lightbulb className="w-3.5 h-3.5" />
              <span>Insights</span>
            </button>
            <button
              onClick={() => setActiveTab("Plans")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activeTab === "Plans"
                ? "bg-indigo-600 text-white font-semibold shadow-sm"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
                }`}
            >
              <CreditCard className="w-3.5 h-3.5" />
              <span>Plans & Pricing</span>
            </button>
            <Link
              to="/codegate"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all text-emerald-400 hover:text-white hover:bg-white/5 shrink-0 whitespace-nowrap"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>CodeGate</span>
            </Link>
          </div>

          {/* Connected GitHub User Info & Action Buttons */}
          <div className="flex items-center space-x-2 flex-wrap sm:flex-nowrap shrink-0">
            <div className="flex items-center space-x-2 bg-[#13161f] border border-emerald-500/25 px-2.5 py-1 rounded-md shrink-0">
              <img
                src={githubUser?.avatar_url || "https://avatars.githubusercontent.com/u/9919?v=4"}
                alt={githubUser?.login}
                className="w-6 h-6 rounded-full border border-emerald-400/40 object-cover shrink-0"
              />
              <div className="flex flex-col justify-center text-left leading-tight py-0.5 min-w-0">
                <span className="text-xs font-semibold text-white font-mono truncate max-w-[140px] whitespace-nowrap block">
                  @{githubUser?.login || githubUsername || "User"}
                </span>
                <span className="text-[10px] text-emerald-400 font-mono flex items-center space-x-1 whitespace-nowrap mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                  <span>{repos.length} Repos Synced</span>
                </span>
              </div>
            </div>

            {/* AST Graph Button */}
            <Link
              to="/graph"
              className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 hover:border-purple-500/60 text-purple-300 hover:text-purple-100 transition-all text-xs font-medium font-poppins group shadow-sm shadow-purple-950/40 shrink-0 whitespace-nowrap"
              title="View AST Code Graph"
            >
              <Network className="w-3.5 h-3.5 text-purple-400 group-hover:rotate-12 transition-transform shrink-0" />
              <span className="whitespace-nowrap">AST Graph</span>
            </Link>

            {/* Admin Panel Button */}
            <Link
              to="/admin"
              className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 hover:border-emerald-500/60 text-emerald-300 hover:text-emerald-100 transition-all text-xs font-medium font-poppins group shadow-sm shadow-emerald-950/40 shrink-0 whitespace-nowrap"
              title="LeakGuard admin panel — CI leak monitoring"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 transition-transform shrink-0" />
              <span className="whitespace-nowrap">Admin</span>
            </Link>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 hover:border-red-500/60 text-red-400 hover:text-red-200 transition-all text-xs font-medium font-poppins group shrink-0 whitespace-nowrap"
              title="Logout"
            >
              <LogOut className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform shrink-0" />
              <span className="whitespace-nowrap">Logout</span>
            </button>
          </div>
        </header>

        {activeTab === "Plans" ? (
          <PricingSection onSelectPlan={(id) => toast.success(`Selected ${id.toUpperCase()} plan`)} />
        ) : (
          <>
            {/* Dashboard Title & GitHub Repository Selector */}
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl md:text-3xl font-semibold text-white tracking-tight font-poppins">
              Amplitude Data AI Overview
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              Live GitHub repository analytics & commit telemetry for @{githubUser?.login || githubUsername}
            </p>
          </div>

          <div className="flex items-center space-x-3 relative">
            {/* Repo Filter Dropdown */}
            <div className="relative">
              <button
                onClick={() => setRepoDropdownOpen(!repoDropdownOpen)}
                className="flex items-center space-x-2 bg-[#15171e] border border-[#252936] hover:border-purple-500/50 text-zinc-300 hover:text-white focus:text-white active:text-white px-4 py-2 rounded-xl text-xs font-mono transition-colors"
              >
                <FolderGit2 className="w-3.5 h-3.5 text-purple-400" />
                <span>{selectedRepo}</span>
                <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
              </button>

              {repoDropdownOpen && (
                <div className="absolute right-0 top-full mt-2 w-64 bg-[#141720] border border-[#272c3d] rounded-2xl shadow-2xl p-2 z-30 max-h-60 overflow-y-auto custom-scrollbar">
                  {repos.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => handleSelectRepo(r.name)}
                      className="w-full text-left px-3 py-2 text-xs font-mono text-zinc-300 hover:bg-purple-600/20 hover:text-purple-200 focus:bg-purple-600/20 focus:text-purple-200 rounded-xl flex items-center justify-between truncate transition-colors"
                    >
                      <span className="truncate">{r.name}</span>
                      <span className="text-[10px] text-purple-400">{r.language || "code"}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={() => {
                if (!selectedRepo) {
                  toast.error("Please select a repository first");
                  return;
                }
                setIsReportOpen(true);
              }}
              className="flex items-center space-x-2 bg-gradient-to-r from-rose-600 to-purple-600 hover:from-rose-500 hover:to-purple-500 text-white px-5 py-2 rounded-xl font-semibold text-xs shadow-lg shadow-rose-950/40 transition-all cursor-pointer whitespace-nowrap"
            >
              <FileBarChart2 className="w-3.5 h-3.5" />
              <span>Get Report</span>
            </button>
          </div>
        </div>

        {/* Main Dashboard Layout (12 Columns) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-5">

          {/* Top 3 Metric Cards (8 cols on lg screen) */}
          <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-[#13151b] border border-[#202430] rounded-2xl p-5 relative overflow-hidden group hover:border-[#303748] transition-all">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium text-zinc-400 flex items-center space-x-2">
                  <FolderGit2 className="w-3.5 h-3.5 text-purple-400" />
                  <span>Public Repositories</span>
                </span>
                <a
                  href={`https://github.com/${githubUser?.login || githubUsername}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-full bg-white/5 text-zinc-400 hover:text-white"
                >
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </a>
              </div>
              <div className="flex items-baseline space-x-3">
                <span className="text-3xl lg:text-4xl font-bold text-white tracking-tight font-poppins">
                  {githubUser?.public_repos || repos.length || 30}
                </span>
                <span className="inline-flex items-center space-x-1 bg-[#16a34a]/20 border border-[#22c55e]/40 text-[#4ade80] px-2 py-0.5 rounded-full text-[11px] font-semibold">
                  <TrendingUp className="w-3 h-3" />
                  <span>+6%</span>
                </span>
              </div>
            </div>

            <div className="bg-[#13151b] border border-[#202430] rounded-2xl p-5 relative overflow-hidden group hover:border-[#303748] transition-all">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium text-zinc-400 flex items-center space-x-2">
                  <User className="w-3.5 h-3.5 text-zinc-400" />
                  <span>GitHub Followers</span>
                </span>
                <a
                  href={`https://github.com/${githubUser?.login || githubUsername}?tab=followers`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-full bg-white/5 text-zinc-400 hover:text-white"
                >
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </a>
              </div>
              <div className="flex items-baseline space-x-3">
                <span className="text-3xl lg:text-4xl font-bold text-white tracking-tight font-poppins">
                  {githubUser?.followers !== undefined ? githubUser.followers : 74}
                </span>
                <span className="inline-flex items-center space-x-1 bg-[#16a34a]/20 border border-[#22c55e]/40 text-[#4ade80] px-2 py-0.5 rounded-full text-[11px] font-semibold">
                  <TrendingUp className="w-3 h-3" />
                  <span>+12%</span>
                </span>
              </div>
            </div>

            <div className="bg-[#13151b] border border-[#202430] rounded-2xl p-5 relative overflow-hidden group hover:border-[#303748] transition-all">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium text-zinc-400 flex items-center space-x-2">
                  <GitCommit className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Recent Commits</span>
                </span>
                <button className="p-1.5 rounded-full bg-white/5 text-zinc-400 hover:text-white">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex items-baseline space-x-3">
                <span className="text-3xl lg:text-4xl font-bold text-white tracking-tight font-poppins">
                  {commits.length || 15}
                </span>
                <span className="inline-flex items-center space-x-1 bg-[#16a34a]/20 border border-[#22c55e]/40 text-[#4ade80] px-2 py-0.5 rounded-full text-[11px] font-semibold">
                  <TrendingUp className="w-3 h-3" />
                  <span>+18%</span>
                </span>
              </div>
            </div>
          </div>

          {/* Left Hero Card: User Activity Heatmap (4 cols) — Real GitHub API Data */}
          {(() => {
            const heatmapData = buildHeatmapFromCommits(commits);
            return (
              <div className="lg:col-span-4 bg-[#13151b] border border-[#202430] rounded-2xl p-5 flex flex-col justify-between lg:row-span-2">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-base md:text-lg font-semibold text-white font-poppins">
                        User Activity Heatmap
                      </h3>
                      <p className="text-[11px] text-zinc-500 font-mono">
                        {selectedRepo} commit activity by day & hour
                      </p>
                    </div>
                    <div className="flex items-center space-x-1.5">
                      {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin text-purple-400" />}
                      <span className="text-[10px] font-mono bg-purple-950 text-purple-300 px-2 py-0.5 rounded border border-purple-800">
                        REAL TIME
                      </span>
                    </div>
                  </div>

                  {/* Heatmap Legend */}
                  <div className="flex items-center justify-between text-[11px] text-zinc-400 mb-4 font-mono">
                    <span className="flex items-center space-x-1.5">
                      <span className="w-3 h-3 bg-[#1e1732] border border-purple-900/60 rounded-xs inline-block" />
                      <span>0 commits</span>
                    </span>
                    <span className="flex items-center space-x-1.5">
                      <span className="w-3 h-3 bg-[#6b46c1] rounded-xs inline-block" />
                      <span>Moderate</span>
                    </span>
                    <span className="flex items-center space-x-1.5">
                      <span className="w-3 h-3 bg-[#a855f7] shadow-[0_0_8px_rgba(168,85,247,0.5)] rounded-xs inline-block" />
                      <span>Peak Activity</span>
                    </span>
                  </div>

                  {/* 6x7 Grid driven by real GitHub commit timestamps */}
                  <div className="space-y-2 mb-6">
                    {times.map((timeLabel, rIdx) => (
                      <div key={rIdx} className="flex items-center space-x-2">
                        <span className="w-10 text-[10px] font-mono text-zinc-500 text-right shrink-0">
                          {timeLabel}
                        </span>
                        <div className="flex-1 grid grid-cols-7 gap-1.5">
                          {days.map((_, cIdx) => {
                            const count = heatmapData.grid[rIdx][cIdx];
                            const isPeak = count > 0 && count === heatmapData.maxCount;
                            const isActive = count > 0;

                            return (
                              <div
                                key={cIdx}
                                title={`${days[cIdx]} @ ${timeLabel}: ${count} commit${count !== 1 ? "s" : ""}`}
                                className={`h-6 rounded-md transition-all duration-200 cursor-pointer flex items-center justify-center text-[10px] font-mono ${isPeak
                                  ? "bg-[#a855f7] text-white font-bold shadow-[0_0_12px_rgba(168,85,247,0.6)] ring-1 ring-purple-300/50 scale-105"
                                  : isActive
                                    ? "bg-[#6b46c1] text-purple-100 hover:scale-110"
                                    : "bg-[#181525] border border-purple-950/40 text-zinc-600 hover:border-purple-800/60"
                                  }`}
                              >
                                {count > 0 ? count : ""}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                    <div className="flex items-center space-x-2 pt-1">
                      <span className="w-10 shrink-0" />
                      <div className="flex-1 grid grid-cols-7 gap-1.5 text-[10px] font-mono text-zinc-500 text-center">
                        {days.map((d) => (
                          <span key={d}>{d}</span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Real Distribution Progress Bar */}
                  <div className="space-y-2 mb-6">
                    <div className="h-2 rounded-full w-full flex overflow-hidden bg-zinc-800 shadow-inner">
                      <div
                        style={{ width: `${heatmapData.nightPct || 10}%` }}
                        className="bg-cyan-400 transition-all duration-500"
                        title={`Night (00:00-08:00): ${heatmapData.nightPct || 0}%`}
                      />
                      <div
                        style={{ width: `${heatmapData.morningPct}%` }}
                        className="bg-purple-600 transition-all duration-500"
                        title={`Morning (08:00-16:00): ${heatmapData.morningPct}%`}
                      />
                      <div
                        style={{ width: `${heatmapData.dayPct}%` }}
                        className="bg-purple-900 transition-all duration-500"
                        title={`Evening (16:00-24:00): ${heatmapData.dayPct}%`}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
                      <span>
                        <strong className="text-cyan-300 font-semibold">{heatmapData.nightPct || 0}%</strong> Night (0-8h)
                      </span>
                      <span>
                        <strong className="text-purple-300 font-semibold">{heatmapData.morningPct}%</strong> Morning (8-16h)
                      </span>
                      <span>
                        <strong className="text-purple-400 font-semibold">{heatmapData.dayPct}%</strong> Evening (16-24h)
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-[#181a23] border border-[#272c3b] rounded-xl p-3.5 flex items-start space-x-3">
                  <Bot className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-zinc-300 leading-relaxed">
                    <strong className="text-white font-medium">AI forecast:</strong> Commit activity for{" "}
                    <span className="text-emerald-400 font-mono font-semibold">@{githubUser?.login || githubUsername}</span>
                    {" "}peaks during <span className="text-purple-300 font-semibold">{heatmapData.peakSlotLabel}</span> development windows ({heatmapData.totalCommits} commits analyzed).
                  </p>
                </div>
              </div>
            );
          })()}

          {/* Middle Left: Commit Timeline Area Chart (5 cols) — real GitHub API data */}
          <div className="lg:col-span-5 bg-[#13151b] border border-[#202430] rounded-2xl p-5 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="text-base md:text-lg font-semibold text-white font-poppins flex items-center space-x-2">
                  <GitCommit className="w-4 h-4 text-emerald-400" />
                  <span>Commit Timeline</span>
                </h3>
                <p className="text-[11px] text-zinc-500 font-mono mt-0.5">
                  {selectedRepo} — daily commit frequency
                </p>
              </div>
              <div className="flex items-center space-x-2">
                {loading && <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />}
                <span className="text-[10px] font-mono bg-emerald-950 text-emerald-400 border border-emerald-700/40 px-2 py-0.5 rounded">
                  LIVE
                </span>
              </div>
            </div>

            <div className="h-[210px] w-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={processCommitTimeline(commits)}
                  margin={{ top: 15, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="commitGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="purpleGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#a855f7" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#a855f7" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222633" vertical={false} />
                  <XAxis dataKey="date" stroke="#52525b" tickLine={false} fontSize={9} interval="preserveStartEnd" />
                  <YAxis stroke="#52525b" tickLine={false} fontSize={10} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: '#13151b',
                      border: '1px solid #272c3d',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontFamily: 'monospace',
                      color: '#e4e4e7',
                    }}
                    formatter={(val: any) => [`${val} commit${val !== 1 ? 's' : ''}`, 'Commits']}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#10b981"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#commitGradient)"
                    dot={{ fill: '#10b981', r: 3, strokeWidth: 0 }}
                    activeDot={{ fill: '#34d399', r: 5, strokeWidth: 2, stroke: '#0f1117' }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>


          {/* Middle Center: AI-derived Comparison (3 cols) */}
          <div className="lg:col-span-3 bg-[#13151b] border border-[#202430] rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base md:text-lg font-semibold text-white font-poppins">AI-derived Comparison</h3>
                <button className="text-zinc-500 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <div className="text-2xl font-bold text-white mb-0.5 font-poppins">82</div>
                  <div className="text-xs text-zinc-400 mb-2">Engagement</div>
                  <div className="space-y-1">
                    {[...Array(9)].map((_, i) => (
                      <div
                        key={i}
                        className={`h-2 rounded-full transition-all ${i >= 2 ? "bg-[#22c55e]" : "bg-zinc-800"
                          }`}
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <div className="text-2xl font-bold text-white mb-0.5 font-poppins">41</div>
                  <div className="text-xs text-zinc-400 mb-2">Satisfaction</div>
                  <div className="space-y-1">
                    {[...Array(9)].map((_, i) => (
                      <div
                        key={i}
                        className={`h-2 rounded-full transition-all ${i >= 5 ? "bg-[#f97316]" : "bg-zinc-800"
                          }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-[#181a23] border border-[#272c3b] rounded-xl p-3 flex items-start space-x-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <p className="text-[11px] text-zinc-300 leading-relaxed">
                <strong className="text-white font-medium">Warning:</strong> Users are willing to engage, but experience does not consistently meet expectations.
              </p>
            </div>
          </div>

          {/* Bottom Row Left: Glowing AI Insights Banner Card (4 cols) */}
          <div className="lg:col-span-4 bg-gradient-to-br from-[#8b5cf6] via-[#7c3aed] to-[#6d28d9] rounded-2xl p-6 text-white flex flex-col justify-between relative overflow-hidden shadow-2xl shadow-purple-600/30">
            <div className="absolute top-0 right-0 p-8 pointer-events-none opacity-20">
              <Sparkles className="w-28 h-28" />
            </div>

            <div>
              <div className="inline-flex items-center space-x-2 bg-white/20 backdrop-blur-md px-3 py-1 rounded-full text-xs font-medium mb-6">
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                <span>GitHub Insights</span>
              </div>

              <h4 className="text-xl md:text-2xl font-medium leading-snug tracking-tight mb-4 font-poppins">
                Improve <span className="bg-white/20 px-2 py-0.5 rounded-lg border border-white/30 font-bold">32%</span> in morning commit activity across @{githubUser?.login || githubUsername}'s public repositories.
              </h4>
            </div>

            <div className="flex space-x-1.5 pt-2">
              <span className="w-6 h-2 bg-white rounded-full" />
              <span className="w-6 h-2 bg-white rounded-full" />
              <span className="w-6 h-2 bg-white rounded-full" />
              <span className="w-6 h-2 bg-white/30 rounded-full" />
              <span className="w-6 h-2 bg-white/30 rounded-full" />
              <span className="w-6 h-2 bg-white/30 rounded-full" />
            </div>
          </div>

          {/* Bottom Row Center: Leak Type Breakdown Donut Chart (4 cols) */}
          <div className="lg:col-span-4 bg-[#13151b] border border-[#202430] rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base md:text-lg font-semibold text-white font-poppins">
                  Leak Breakdown
                </h3>
                <button className="flex items-center space-x-1 text-xs text-zinc-400 bg-[#171a22] border border-[#252a36] px-3 py-1 rounded-lg">
                  <span>All Severities</span>
                  <ChevronDown className="w-3 h-3" />
                </button>
              </div>

              <div className="flex items-center space-x-5 mb-4">
                {/* SVG Donut Chart */}
                <div className="relative w-28 h-28 flex items-center justify-center flex-shrink-0">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-purple-950"
                      strokeWidth="3.8"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className="text-purple-500"
                      strokeDasharray="70, 100"
                      strokeWidth="3.8"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className="text-cyan-400"
                      strokeDasharray="40, 100"
                      strokeWidth="3.8"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <span className="text-base font-bold text-white leading-tight font-poppins">
                      248
                    </span>
                    <span className="text-[10px] text-zinc-400 font-poppins">Leaks</span>
                  </div>
                </div>

                {/* Age breakdown list */}
                <div className="flex-1 space-y-1 text-xs">
                  <div className="flex justify-between items-center text-zinc-300">
                    <span className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                      <span>File handles</span>
                    </span>
                    <span className="font-mono font-semibold">40%</span>
                  </div>
                  <div className="flex justify-between items-center text-zinc-400">
                    <span className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-purple-500 inline-block" />
                      <span>Network sockets</span>
                    </span>
                    <span className="font-mono font-semibold">25%</span>
                  </div>
                  <div className="flex justify-between items-center text-zinc-400">
                    <span className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-purple-700 inline-block" />
                      <span>DB connections</span>
                    </span>
                    <span className="font-mono font-semibold">20%</span>
                  </div>
                  <div className="flex justify-between items-center text-zinc-500">
                    <span className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-purple-900 inline-block" />
                      <span>Locks &amp; threads</span>
                    </span>
                    <span className="font-mono font-semibold">10%</span>
                  </div>
                  <div className="flex justify-between items-center text-zinc-500">
                    <span className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-slate-700 inline-block" />
                      <span>Other</span>
                    </span>
                    <span className="font-mono font-semibold">5%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-[#181a23] border border-[#272c3b] rounded-xl p-2.5 flex items-start space-x-2 text-[11px] text-zinc-300">
              <Bot className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
              <span><strong className="text-white font-medium">AI note:</strong> Most leaks are unclosed file handles on early-return paths.</span>
            </div>
          </div>

          {/* Bottom Row Right: Cleanup Coverage Radial Gauge Card (4 cols) */}
          <div className="lg:col-span-4 bg-[#13151b] border border-[#202430] rounded-2xl p-5 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-base md:text-lg font-semibold text-white font-poppins">
                Cleanup Coverage
              </h3>
              <a
                href={`https://github.com/${githubUser?.login || githubUsername}`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-full bg-white/5 text-zinc-400 hover:text-white"
              >
                <ArrowUpRight className="w-4 h-4" />
              </a>
            </div>

            {/* Custom SVG Radial Arc Gauge */}
            <div className="flex flex-col items-center justify-center my-2">
              <svg viewBox="0 0 200 115" className="w-64 h-36">
                {Array.from({ length: 25 }).map((_, i) => {
                  const angle = -180 + (i * 180) / 24;
                  const rad = (angle * Math.PI) / 180;
                  const rInner = 62;
                  const rOuter = 82;
                  const x1 = 100 + rInner * Math.cos(rad);
                  const y1 = 98 + rInner * Math.sin(rad);
                  const x2 = 100 + rOuter * Math.cos(rad);
                  const y2 = 98 + rOuter * Math.sin(rad);
                  const isActive = i < 16;
                  return (
                    <line
                      key={i}
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke={isActive ? "#8b5cf6" : "#262936"}
                      strokeWidth="3.5"
                      strokeLinecap="round"
                    />
                  );
                })}
                <text x="100" y="82" textAnchor="middle" className="text-3xl font-bold fill-white font-poppins">
                  64%
                </text>
                <text x="100" y="98" textAnchor="middle" className="text-[11px] fill-zinc-400 font-poppins">
                  Paths cleaned up
                </text>
              </svg>
            </div>

            <div className="text-[11px] text-zinc-500 text-center font-mono pt-1">
              Recomputed on every CodeGate analysis run
            </div>
          </div>

        </div>

        {/* DEDICATED PROJECT COMMIT HISTORY & COMMIT LOGS PANEL */}
        <section className="bg-[#13151b] border border-[#202430] rounded-2xl p-6 space-y-5">
          {/* Section Title & Search */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-[#1f2432] pb-4">
            <div>
              <div className="flex items-center space-x-2 mb-1">
                <GitCommit className="w-5 h-5 text-emerald-400 animate-pulse" />
                <h3 className="text-xl font-bold text-white font-poppins tracking-tight">
                  Project Commit History & Commit Logs
                </h3>
              </div>
              <p className="text-xs text-zinc-400">
                Real-time commit telemetry & commit history for repository:{" "}
                <span className="text-purple-400 font-mono font-semibold">{selectedRepo}</span>
              </p>
            </div>

            <div className="flex items-center space-x-3 w-full md:w-auto">
              <div className="relative flex-1 md:w-64">
                <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchCommitQuery}
                  onChange={(e) => setSearchCommitQuery(e.target.value)}
                  placeholder="Search commit logs or SHAs..."
                  className="w-full bg-[#181b24] border border-[#272c3d] focus:border-purple-500 text-white placeholder-zinc-500 pl-9 pr-3 py-2 rounded-xl text-xs outline-none"
                />
              </div>

              <button
                onClick={() => loadDashboardGitHubData(githubUsername)}
                className="p-2 rounded-xl bg-[#181b24] border border-[#272c3d] hover:bg-[#202533] text-zinc-300 hover:text-white transition-colors"
                title="Refresh GitHub API"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-purple-400" : ""}`} />
              </button>
            </div>
          </div>

          {/* Repository Selector Pill Tabs */}
          <div className="flex items-center space-x-2 overflow-x-auto pb-2 scrollbar-purple">
            <span className="text-xs font-mono text-zinc-500 uppercase tracking-widest flex items-center space-x-1 mr-2 flex-shrink-0">
              <FolderGit2 className="w-3.5 h-3.5 text-purple-400" />
              <span>PROJECTS:</span>
            </span>

            {repos.map((r) => {
              const isSelected = selectedRepo === r.name;
              return (
                <button
                  key={r.id}
                  onClick={() => handleSelectRepo(r.name)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-mono flex items-center space-x-2 transition-all flex-shrink-0 cursor-pointer ${isSelected
                    ? "bg-purple-600 text-white font-semibold shadow-lg shadow-purple-600/30 border border-purple-400/50"
                    : "bg-[#181b24] text-zinc-400 hover:text-white border border-[#262b3a]"
                    }`}
                >
                  <GitBranch className="w-3 h-3" />
                  <span>{r.name}</span>
                  {r.language && (
                    <span className="text-[10px] opacity-75">({r.language})</span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Real Commit Logs Table Stream */}
          <div className="overflow-hidden border border-[#222736] rounded-xl bg-[#0f1117]">
            <div className="grid grid-cols-12 bg-[#171a24] border-b border-[#222736] p-3 text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
              <span className="col-span-3 md:col-span-2">COMMIT SHA</span>
              <span className="col-span-6 md:col-span-5">COMMIT LOG MESSAGE</span>
              <span className="hidden md:block md:col-span-2">AUTHOR</span>
              <span className="col-span-3 md:col-span-3 text-right">TIMESTAMP & ACTIONS</span>
            </div>

            <div className="divide-y divide-[#1e2230] max-h-[380px] overflow-y-auto scrollbar-emerald">
              {filteredCommits.length > 0 ? (
                filteredCommits.map((commit) => (
                  <div
                    key={commit.sha}
                    className="grid grid-cols-12 items-center p-3.5 text-xs font-mono hover:bg-white/5 transition-colors group"
                  >
                    {/* SHA Badge */}
                    <div className="col-span-3 md:col-span-2 flex items-center space-x-2">
                      <span className="inline-flex items-center space-x-1 bg-emerald-950/90 border border-emerald-500/40 text-emerald-400 px-2 py-1 rounded-md text-[11px] font-mono font-semibold">
                        <GitCommit className="w-3 h-3" />
                        <span>{commit.sha}</span>
                      </span>
                      <button
                        onClick={() => handleCopySha(commit.sha)}
                        className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-zinc-300 transition-opacity p-1"
                        title="Copy SHA"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                    </div>

                    {/* Commit Message */}
                    <div className="col-span-6 md:col-span-5 pr-2">
                      <p className="text-zinc-200 font-medium truncate group-hover:text-purple-300">
                        {commit.message}
                      </p>
                    </div>

                    {/* Author */}
                    <div className="hidden md:flex md:col-span-2 items-center space-x-2">
                      <img
                        src={commit.authorAvatar}
                        alt={commit.authorName}
                        className="w-5 h-5 rounded-full border border-purple-500/40"
                      />
                      <span className="text-zinc-400 text-xs truncate">
                        {commit.authorName}
                      </span>
                    </div>

                    {/* Timestamp & Action */}
                    <div className="col-span-3 md:col-span-3 flex items-center justify-end space-x-3 text-right">
                      <span className="text-zinc-500 text-[11px] hidden sm:inline-block">
                        {new Date(commit.date).toLocaleDateString()}
                      </span>
                      <a
                        href={commit.htmlUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1 bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2.5 py-1 rounded-lg text-[11px] font-mono transition-colors"
                      >
                        <span>View</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs font-mono text-zinc-500">
                  {loading
                    ? "Fetching real-time commit logs from GitHub API..."
                    : `No commit logs found matching "${searchCommitQuery}".`}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ── COMMIT ACTIVITY TIMELINE GRAPH (full-width) ── */}
        <section className="bg-[#13151b] border border-[#202430] rounded-2xl p-6 space-y-5">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-[#1f2432] pb-4">
            <div>
              <div className="flex items-center space-x-2 mb-1">
                <TrendingUp className="w-5 h-5 text-purple-400" />
                <h3 className="text-xl font-bold text-white font-poppins tracking-tight">
                  Commit Activity — Full Timeline Graph
                </h3>
              </div>
              <p className="text-xs text-zinc-400">
                All-time daily commit frequency for{" "}
                <span className="text-emerald-400 font-mono font-semibold">{selectedRepo}</span>
                {" "}sourced live from GitHub REST API.
              </p>
            </div>
            <div className="flex items-center space-x-3">
              {loading && <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />}
              <span className="text-[10px] font-mono bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded">
                REAL TIME
              </span>
            </div>
          </div>

          {/* Metric mini row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-[#0f1117] border border-[#202430] rounded-xl p-4 text-center">
              <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Total Commits</p>
              <p className="text-2xl font-bold text-white font-poppins">{commits.length}</p>
            </div>
            <div className="bg-[#0f1117] border border-[#202430] rounded-xl p-4 text-center">
              <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Unique Days</p>
              <p className="text-2xl font-bold text-emerald-400 font-poppins">
                {processCommitTimeline(commits).length}
              </p>
            </div>
            <div className="bg-[#0f1117] border border-[#202430] rounded-xl p-4 text-center">
              <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Peak Day</p>
              <p className="text-xl font-bold text-purple-400 font-poppins truncate">
                {processCommitTimeline(commits).reduce(
                  (a, b) => (a.count > b.count ? a : b),
                  { date: "—", count: 0 }
                ).date}
              </p>
            </div>
            <div className="bg-[#0f1117] border border-[#202430] rounded-xl p-4 text-center">
              <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Max / Day</p>
              <p className="text-2xl font-bold text-amber-400 font-poppins">
                {processCommitTimeline(commits).reduce(
                  (a, b) => (a.count > b.count ? a : b),
                  { date: "", count: 0 }
                ).count}
              </p>
            </div>
          </div>

          {/* Full-width timeline chart */}
          <div className="h-[260px] w-full bg-[#0f1117] border border-[#202430] rounded-xl p-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={processCommitTimeline(commits)}
                margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="fullCommitGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2230" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="#3f4454"
                  tickLine={false}
                  fontSize={10}
                  fontFamily="monospace"
                  interval="preserveStartEnd"
                />
                <YAxis
                  stroke="#3f4454"
                  tickLine={false}
                  fontSize={10}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    background: '#0d0e12',
                    border: '1px solid #8b5cf6',
                    borderRadius: '14px',
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    color: '#e4e4e7',
                    boxShadow: '0 0 24px rgba(139,92,246,0.25)',
                  }}
                  cursor={{ stroke: '#8b5cf6', strokeWidth: 1, strokeDasharray: '4 2' }}
                  formatter={(val: any) => [`${val} commit${val !== 1 ? 's' : ''}`, 'Activity']}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#8b5cf6"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#fullCommitGrad)"
                  dot={false}
                  activeDot={{ fill: '#a78bfa', r: 6, strokeWidth: 2, stroke: '#0d0e12' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
        </>
        )}

      </div>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      {/* Leak Report Modal */}
      <LeakReportModal
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        owner={githubUser?.login || githubUsername}
        repo={selectedRepo}
        branch={repos.find((r) => r.name === selectedRepo)?.default_branch || "main"}
      />
    </div>
  );
}
