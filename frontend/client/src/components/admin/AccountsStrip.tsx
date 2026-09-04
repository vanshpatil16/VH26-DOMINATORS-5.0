/**
 * Account switcher: the watched GitHub accounts as a single horizontal row,
 * with the access token tucked behind a disclosure rather than occupying a
 * permanent column.
 */
import React, { useState } from "react";
import {
  Plus,
  X,
  KeyRound,
  Check,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import type { LevelCounts } from "@/lib/leakMonitor";
import type { GitHubUser } from "@/lib/github";
import { SEVERITY } from "./chartTheme";

export interface AccountSummary {
  login: string;
  user: GitHubUser | null;
  repoCount: number;
  scannedRepos: number;
  counts: LevelCounts;
  loading: boolean;
  error: string | null;
}

interface Props {
  accounts: AccountSummary[];
  selected: string | null;
  onSelect: (login: string) => void;
  onAdd: (login: string) => void;
  onRemove: (login: string) => void;
  onRescan: (login: string) => void;
  tokenPresent: boolean;
  tokenOwner: string | null;
  tokenError: string | null;
  tokenChecking: boolean;
  onSaveToken: (token: string) => void;
  onClearToken: () => void;
}

export default function AccountsStrip({
  accounts,
  selected,
  onSelect,
  onAdd,
  onRemove,
  onRescan,
  tokenPresent,
  tokenOwner,
  tokenError,
  tokenChecking,
  onSaveToken,
  onClearToken,
}: Props) {
  const [adding, setAdding] = useState(false);
  const [newLogin, setNewLogin] = useState("");
  const [tokenOpen, setTokenOpen] = useState(false);
  const [tokenDraft, setTokenDraft] = useState("");

  const submitAccount = () => {
    const login = newLogin.trim().replace(/^@/, "");
    if (!login) return;
    onAdd(login);
    setNewLogin("");
    setAdding(false);
  };

  const saveToken = () => {
    if (!tokenDraft.trim()) return;
    onSaveToken(tokenDraft.trim());
    setTokenDraft("");
  };

  return (
    <div className="rounded-2xl border border-[#1e2230] bg-[#13151b]">
      <div className="flex flex-wrap items-center gap-2 p-3">
        <span className="mr-1 text-xs font-medium uppercase tracking-wider text-zinc-500">
          Accounts
        </span>

        {accounts.map(acc => {
          const active = selected === acc.login;
          return (
            <div
              key={acc.login}
              className={`group flex items-center gap-2 rounded-xl border py-1.5 pl-1.5 pr-2 transition-colors ${
                active
                  ? "border-purple-500/50 bg-purple-500/10"
                  : "border-[#242938] bg-[#0f1117] hover:border-purple-500/30"
              }`}
            >
              <button
                onClick={() => onSelect(acc.login)}
                className="flex items-center gap-2"
                title={acc.error ?? `${acc.repoCount} repositories`}
              >
                <img
                  src={acc.user?.avatar_url || "https://github.com/github.png"}
                  alt=""
                  className="h-6 w-6 rounded-full object-cover ring-1 ring-black/40"
                />
                <span className={`text-xs font-medium ${active ? "text-white" : "text-zinc-300"}`}>
                  {acc.login}
                </span>

                {acc.loading ? (
                  <Loader2 className="h-3 w-3 animate-spin text-purple-400" />
                ) : acc.counts.error > 0 ? (
                  <span
                    className="rounded-full px-1.5 py-px text-[10px] font-semibold tabular-nums"
                    style={{ background: "rgba(208,59,59,0.16)", color: "#f0a3a3" }}
                  >
                    {acc.counts.error}
                  </span>
                ) : acc.scannedRepos > 0 ? (
                  <span className="text-[10px] text-emerald-500/80">clear</span>
                ) : null}
              </button>

              <span className="flex items-center opacity-0 transition-opacity group-hover:opacity-100">
                <button
                  onClick={() => onRescan(acc.login)}
                  title={`Re-scan @${acc.login}`}
                  className="rounded p-0.5 text-zinc-500 hover:text-cyan-300"
                >
                  <RefreshCw className="h-3 w-3" />
                </button>
                <button
                  onClick={() => onRemove(acc.login)}
                  title={`Stop watching @${acc.login}`}
                  className="rounded p-0.5 text-zinc-500 hover:text-rose-400"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            </div>
          );
        })}

        {adding ? (
          <span className="flex items-center gap-1.5 rounded-xl border border-purple-500/40 bg-[#0f1117] py-1 pl-2.5 pr-1">
            <input
              autoFocus
              value={newLogin}
              onChange={e => setNewLogin(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") submitAccount();
                if (e.key === "Escape") { setAdding(false); setNewLogin(""); }
              }}
              placeholder="github login"
              className="w-32 bg-transparent text-xs text-white placeholder-zinc-600 outline-none"
            />
            <button
              onClick={submitAccount}
              className="rounded-lg p-1 text-zinc-400 hover:text-emerald-300"
              title="Watch this account"
            >
              <Check className="h-3.5 w-3.5" />
            </button>
          </span>
        ) : (
          <button
            onClick={() => setAdding(true)}
            className="flex items-center gap-1.5 rounded-xl border border-dashed border-[#2a3040] px-2.5 py-1.5 text-xs text-zinc-400 transition-colors hover:border-purple-500/40 hover:text-white"
          >
            <Plus className="h-3.5 w-3.5" />
            Watch account
          </button>
        )}

        <button
          onClick={() => setTokenOpen(o => !o)}
          className={`flex items-center gap-1.5 rounded-xl border px-2.5 py-1.5 text-xs transition-colors sm:ml-auto ${
            tokenOpen
              ? "border-amber-500/40 bg-amber-500/10 text-amber-200"
              : "border-[#242938] bg-[#0f1117] text-zinc-400 hover:text-white"
          }`}
        >
          {tokenChecking ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : tokenPresent && tokenOwner ? (
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <KeyRound className="h-3.5 w-3.5" style={{ color: SEVERITY.warning }} />
          )}
          {tokenPresent && tokenOwner ? `Token · ${tokenOwner}` : "No token · public only"}
        </button>
      </div>

      {tokenOpen && (
        <div className="border-t border-[#1e2230] px-3 py-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <p className="flex-1 text-xs leading-relaxed text-zinc-500">
              A personal access token with <code className="text-zinc-400">repo</code> and{" "}
              <code className="text-zinc-400">checks:read</code> reads private repositories
              and raises the API budget from 60 to 5,000 calls an hour. Stored in this
              browser only.
            </p>
            <div className="flex gap-2">
              <input
                type="password"
                value={tokenDraft}
                onChange={e => setTokenDraft(e.target.value)}
                onKeyDown={e => e.key === "Enter" && saveToken()}
                placeholder="ghp_…"
                className="w-48 rounded-lg border border-[#242938] bg-[#0f1117] px-3 py-1.5 font-mono text-[11px] text-white placeholder-zinc-600 outline-none transition-colors focus:border-amber-500"
              />
              <button
                onClick={saveToken}
                className="rounded-lg border border-[#242938] bg-[#0f1117] px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:border-emerald-500/50 hover:text-white"
              >
                Save
              </button>
              {tokenPresent && (
                <button
                  onClick={onClearToken}
                  className="rounded-lg border border-[#242938] bg-[#0f1117] px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:border-rose-500/50 hover:text-white"
                >
                  Remove
                </button>
              )}
            </div>
          </div>
          {tokenError && (
            <p className="mt-2 flex items-center gap-1.5 text-[11px] text-rose-400">
              <AlertTriangle className="h-3 w-3" />
              {tokenError}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
