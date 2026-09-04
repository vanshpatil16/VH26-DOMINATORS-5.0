import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useLocation } from "wouter";
import {
  X,
  Check,
  Mail,
  ArrowRight,
  Sparkles,
  RefreshCw,
  Github,
  GitBranch,
  GitCommit,
  ExternalLink,
  Code,
  FolderGit2,
  ChevronRight,
  ChevronDown,
  LayoutDashboard,
} from "lucide-react";
import { toast } from "sonner";
import {
  fetchGitHubUser,
  fetchUserRepos,
  fetchRepoCommits,
  GitHubRepo,
  GitHubCommit,
  GitHubUser,
} from "../lib/github";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: "signup" | "login";
}

export default function AuthModal({
  isOpen,
  onClose,
  initialMode = "signup",
}: AuthModalProps) {
  const [, setLocation] = useLocation();
  const [mode, setMode] = useState<"signup" | "login">(initialMode);
  const [email, setEmail] = useState("");
  const [usernameInput, setUsernameInput] = useState("OmkarKudalkar23");
  const [isGithubConnected, setIsGithubConnected] = useState(false);
  const [isConnectingGithub, setIsConnectingGithub] = useState(false);
  
  const [githubUser, setGithubUser] = useState<GitHubUser | null>(null);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [commits, setCommits] = useState<GitHubCommit[]>([]);
  const [loadingCommits, setLoadingCommits] = useState(false);

  useEffect(() => {
    const savedUser = localStorage.getItem("connected_github_user");
    if (savedUser) {
      loadGitHubData(savedUser, false);
    }
  }, []);

  const loadGitHubData = async (userToFetch: string, autoRedirect = true) => {
    setIsConnectingGithub(true);
    const userInfo = await fetchGitHubUser(userToFetch);
    const userRepos = await fetchUserRepos(userToFetch);

    if (userInfo && userRepos.length > 0) {
      setGithubUser(userInfo);
      setRepos(userRepos);
      setIsGithubConnected(true);
      localStorage.setItem("connected_github_user", userToFetch);
      
      // Load commits for first repo by default
      if (userRepos[0]) {
        setSelectedRepo(userRepos[0].name);
        fetchCommitsForRepo(userToFetch, userRepos[0].name);
      }

      if (autoRedirect) {
        toast.success(`GitHub connected: @${userToFetch}`, {
          description: "Redirecting to Dashboard...",
        });
        setTimeout(() => {
          onClose();
          setLocation("/dashboard");
        }, 800);
      } else {
        toast.success(`GitHub account synced: @${userToFetch}`);
      }
    } else {
      toast.error(`Could not fetch GitHub data for @${userToFetch}`);
    }
    setIsConnectingGithub(false);
  };

  const fetchCommitsForRepo = async (user: string, repoName: string) => {
    setLoadingCommits(true);
    const repoCommits = await fetchRepoCommits(user, repoName);
    setCommits(repoCommits);
    setLoadingCommits(false);
  };

  const handleSelectRepo = (repoName: string) => {
    if (selectedRepo === repoName) {
      setSelectedRepo(null);
    } else {
      setSelectedRepo(repoName);
      if (githubUser) {
        fetchCommitsForRepo(githubUser.login, repoName);
      }
    }
  };

  const handleDisconnectGithub = () => {
    setIsGithubConnected(false);
    setGithubUser(null);
    setRepos([]);
    setCommits([]);
    localStorage.removeItem("connected_github_user");
    toast.info("GitHub account disconnected.");
  };

  const handleGoToDashboard = () => {
    onClose();
    setLocation("/dashboard");
  };

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    toast.success(`Welcome back! Redirecting to Dashboard...`);
    setTimeout(() => {
      onClose();
      setLocation("/dashboard");
    }, 600);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/80 backdrop-blur-md"
          />

          {/* Modal Card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="relative w-full max-w-xl bg-[#0d0e12] border border-[#232734] rounded-3xl p-6 md:p-8 shadow-2xl z-10 overflow-hidden text-white max-h-[90vh] flex flex-col"
          >
            {/* Ambient Background Glow */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />

            {/* Header & Close Button */}
            <div className="flex items-center justify-between mb-5 flex-shrink-0">
              <div className="flex items-center space-x-2 bg-white/5 border border-white/10 px-3 py-1 rounded-full text-xs font-mono text-zinc-300">
                <Sparkles className="w-3 h-3 text-purple-400" />
                <span>GITHUB AUTHENTICATION</span>
              </div>

              <button
                onClick={onClose}
                className="p-2 rounded-full bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Container */}
            <div className="overflow-y-auto pr-1 space-y-5 flex-1 custom-scrollbar">
              {/* Modal Title */}
              <div>
                <h3 className="text-2xl font-bold tracking-tight text-white mb-1 font-poppins">
                  {mode === "signup" ? "Connect GitHub Account" : "Sign In to CodeGate"}
                </h3>
                <p className="text-xs text-zinc-400">
                  Sync your GitHub repositories, commits, and PRs automatically into your dashboard.
                </p>
              </div>

              {/* GitHub OAuth Connection Panel */}
              {!isGithubConnected ? (
                <div className="space-y-3 bg-[#13151c] border border-[#242938] rounded-2xl p-4">
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={usernameInput}
                      onChange={(e) => setUsernameInput(e.target.value)}
                      placeholder="GitHub Username (e.g. OmkarKudalkar23)"
                      className="flex-1 bg-[#1a1d26] border border-[#2c3244] focus:border-purple-500 text-white placeholder-zinc-500 px-3.5 py-2.5 rounded-xl text-xs font-mono outline-none"
                    />
                  </div>

                  <button
                    onClick={() => loadGitHubData(usernameInput || "OmkarKudalkar23", true)}
                    disabled={isConnectingGithub}
                    className="w-full flex items-center justify-center space-x-3 bg-[#24292e] hover:bg-[#2f363d] text-white py-3.5 px-4 rounded-xl font-medium text-sm border border-white/15 shadow-xl transition-all group disabled:opacity-60 cursor-pointer"
                  >
                    {isConnectingGithub ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-zinc-300" />
                    ) : (
                      <Github className="w-4 h-4 text-white group-hover:scale-110 transition-transform" />
                    )}
                    <span>
                      {isConnectingGithub
                        ? "Fetching GitHub Repositories & API Data..."
                        : `Authorize GitHub & Open Dashboard (@${usernameInput || "OmkarKudalkar23"})`}
                    </span>
                  </button>
                </div>
              ) : (
                /* Connected State with Real Repos & Commits & Go To Dashboard Button */
                <div className="space-y-4">
                  {/* User Profile Card */}
                  <div className="bg-[#151821] border border-emerald-500/40 rounded-2xl p-4 space-y-3 shadow-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <img
                          src={githubUser?.avatar_url}
                          alt={githubUser?.name || githubUser?.login}
                          className="w-11 h-11 rounded-full border border-emerald-400/50 object-cover shadow-md"
                        />
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm font-semibold text-white font-poppins">
                              {githubUser?.name || githubUser?.login}
                            </span>
                            <span className="inline-flex items-center space-x-1 bg-emerald-500/20 text-emerald-300 text-[10px] font-mono px-2 py-0.5 rounded-full border border-emerald-500/30">
                              <Check className="w-3 h-3" />
                              <span>Connected</span>
                            </span>
                          </div>
                          <span className="text-xs text-zinc-400 font-mono">
                            @{githubUser?.login} • {repos.length} Repositories Synced
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={handleDisconnectGithub}
                        className="text-xs text-zinc-400 hover:text-red-400 font-mono transition-colors border border-white/10 px-3 py-1.5 rounded-lg bg-white/5"
                      >
                        Disconnect
                      </button>
                    </div>

                    {/* Primary Button to Redirect to Dashboard */}
                    <button
                      onClick={handleGoToDashboard}
                      className="w-full flex items-center justify-center space-x-2 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white py-3 px-4 rounded-xl font-medium text-xs shadow-lg shadow-purple-600/30 transition-all cursor-pointer font-poppins"
                    >
                      <LayoutDashboard className="w-4 h-4" />
                      <span>Open Insighta Dashboard</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Synced Repositories & Commit History List */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono text-zinc-400 px-1">
                      <span className="flex items-center space-x-1">
                        <FolderGit2 className="w-3.5 h-3.5 text-purple-400" />
                        <span>SYNCED REPOSITORIES ({repos.length})</span>
                      </span>
                      <span>Click to view commits</span>
                    </div>

                    <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                      {repos.slice(0, 8).map((repo) => {
                        const isExpanded = selectedRepo === repo.name;
                        return (
                          <div
                            key={repo.id}
                            className="bg-[#14171f] border border-[#222735] hover:border-[#32394c] rounded-xl overflow-hidden transition-all"
                          >
                            <button
                              onClick={() => handleSelectRepo(repo.name)}
                              className="w-full p-3 flex items-center justify-between text-left cursor-pointer"
                            >
                              <div className="flex items-center space-x-2.5">
                                <GitBranch className="w-4 h-4 text-purple-400" />
                                <span className="text-xs font-semibold text-white font-mono">
                                  {repo.name}
                                </span>
                                {repo.language && (
                                  <span className="text-[10px] font-mono bg-purple-950/80 border border-purple-800/60 text-purple-300 px-2 py-0.5 rounded-md">
                                    {repo.language}
                                  </span>
                                )}
                              </div>

                              <div className="flex items-center space-x-2">
                                <a
                                  href={repo.html_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-zinc-500 hover:text-white p-1"
                                >
                                  <ExternalLink className="w-3.5 h-3.5" />
                                </a>
                                {isExpanded ? (
                                  <ChevronDown className="w-4 h-4 text-zinc-400" />
                                ) : (
                                  <ChevronRight className="w-4 h-4 text-zinc-400" />
                                )}
                              </div>
                            </button>

                            {/* Expanded Commit History List for this Repo */}
                            {isExpanded && (
                              <div className="bg-[#0f1117] border-t border-[#1f2432] p-3 space-y-2 text-xs">
                                <div className="text-[10px] font-mono text-zinc-400 flex items-center justify-between">
                                  <span className="flex items-center space-x-1">
                                    <GitCommit className="w-3 h-3 text-emerald-400" />
                                    <span>REAL COMMIT HISTORY FOR {repo.name.toUpperCase()}</span>
                                  </span>
                                  {loadingCommits && (
                                    <RefreshCw className="w-3 h-3 animate-spin text-purple-400" />
                                  )}
                                </div>

                                {commits.length > 0 ? (
                                  <div className="space-y-1.5 max-h-[140px] overflow-y-auto">
                                    {commits.map((commit) => (
                                      <a
                                        key={commit.sha}
                                        href={commit.htmlUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-start justify-between p-2 rounded-lg bg-[#151821] hover:bg-[#1c202c] border border-white/5 transition-colors group"
                                      >
                                        <div className="space-y-0.5 max-w-[80%]">
                                          <p className="text-[11px] font-mono text-zinc-200 truncate group-hover:text-purple-300">
                                            {commit.message}
                                          </p>
                                          <div className="flex items-center space-x-2 text-[9px] font-mono text-zinc-500">
                                            <span>{commit.authorName}</span>
                                            <span>•</span>
                                            <span>{new Date(commit.date).toLocaleDateString()}</span>
                                          </div>
                                        </div>
                                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/50">
                                          {commit.sha}
                                        </span>
                                      </a>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-[11px] font-mono text-zinc-500 py-1">
                                    {loadingCommits ? "Fetching commits from GitHub API..." : "No recent commits found."}
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Divider */}
              <div className="relative flex items-center justify-center pt-2">
                <div className="border-t border-[#222634] w-full" />
                <span className="absolute bg-[#0d0e12] px-3 text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
                  OR WITH EMAIL
                </span>
              </div>

              {/* Email Form */}
              <form onSubmit={handleEmailSubmit} className="space-y-3">
                <div>
                  <label className="block text-xs font-mono text-zinc-400 mb-1.5">
                    WORK EMAIL
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@company.com"
                      required
                      className="w-full bg-[#15171e] border border-[#262a38] focus:border-purple-500 text-white placeholder-zinc-500 pl-10 pr-4 py-2.5 rounded-xl text-xs outline-none transition-colors"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full flex items-center justify-center space-x-2 bg-white hover:bg-zinc-200 text-black py-2.5 rounded-xl font-medium text-xs transition-all shadow-lg cursor-pointer"
                >
                  <span>
                    {mode === "signup"
                      ? "Create Account & Open Dashboard"
                      : "Sign In & Open Dashboard"}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>

            {/* Footer Mode Toggle */}
            <div className="text-center pt-3 mt-2 border-t border-[#1f2330] flex-shrink-0">
              <p className="text-xs text-zinc-400">
                {mode === "signup"
                  ? "Already have an account?"
                  : "Don't have an account?"}{" "}
                <button
                  type="button"
                  onClick={() =>
                    setMode(mode === "signup" ? "login" : "signup")
                  }
                  className="text-white hover:underline font-semibold ml-1 cursor-pointer"
                >
                  {mode === "signup" ? "Log in" : "Sign up"}
                </button>
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
