/*
 * Linear Editorial Fidelity: the homepage uses a near-black Swiss editorial canvas,
 * DM Sans for interface copy, IBM Plex Mono for systems labels, hairline rules,
 * asymmetric whitespace, and instrument-like motion rather than decorative effects.
 */
import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  ChevronDown,
  Command,
  CornerDownRight,
  Inbox,
  Layers3,
  Menu,
  MoreHorizontal,
  Play,
  Plus,
  Search,
  Sparkles,
  X,
} from "lucide-react";

const logoMark = "/manus-storage/linear-stripe-mark_5d589de8.png";
const heroImage = "/manus-storage/linear-hero-system_283309c0.jpg";
const purposeImage = "/manus-storage/linear-figure-purpose_fce42799.jpg";
const agentsImage = "/manus-storage/linear-figure-agents_577b8fb2.jpg";
const speedImage = "/manus-storage/linear-figure-speed_62925243.jpg";

const navLinks = [
  { label: "Product", href: "#product", dropdown: ["Intake", "Plan", "AI", "Build"] },
  { label: "Resources", href: "#resources", dropdown: ["Customers", "Now", "Contact"] },
  { label: "Customers", href: "#customers" },
  { label: "Pricing", href: "#pricing" },
  { label: "Now", href: "#now" },
  { label: "Contact", href: "#contact" },
];

const figures = [
  {
    index: "FIG 0.1",
    title: "Purpose-built",
    copy: "Linear is shaped by the practices and principles of world-class product teams.",
    image: purposeImage,
  },
  {
    index: "FIG 0.2",
    title: "Powered by agents",
    copy: "Designed for workflows shared by humans and agents, from drafting PRDs to pushing PRs.",
    image: agentsImage,
  },
  {
    index: "FIG 0.3",
    title: "Designed for speed",
    copy: "Reduces noise and restores momentum to help teams ship with high velocity and focus.",
    image: speedImage,
  },
];

const intakeIssues = [
  ["ENG-2085", "Reduce UI flicker during autonomy...", "Backlog"],
  ["ENG-2094", "Add buffering for autonomy event streams", "Backlog"],
  ["ENG-2092", "Reduce startup delay caused by vehicle sync", "Backlog"],
  ["ENG-2200", "Fix delayed route updates during rerouting", "Backlog"],
  ["ENG-0926", "Remove UI inconsistencies", "Todo"],
];

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return { ref, visible };
}

function LinearMark({ className = "" }: { className?: string }) {
  return (
    <img
      className={`linear-mark ${className}`}
      src={logoMark}
      alt=""
      aria-hidden="true"
    />
  );
}

function Nav() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  return (
    <header className="site-nav" data-menu-open={menuOpen}>
      <div className="nav-inner">
        <a className="wordmark" href="#top" aria-label="Linear home">
          <LinearMark />
          <span>Linear</span>
        </a>

        <nav className="desktop-nav" aria-label="Main navigation">
          {navLinks.map((link) => (
            <div className="nav-item" key={link.label}>
              {link.dropdown ? (
                <button
                  className="nav-link nav-dropdown-trigger"
                  type="button"
                  aria-expanded={openDropdown === link.label}
                  onClick={() => setOpenDropdown(openDropdown === link.label ? null : link.label)}
                >
                  {link.label}
                  <ChevronDown size={13} strokeWidth={1.7} />
                </button>
              ) : (
                <a className="nav-link" href={link.href}>
                  {link.label}
                </a>
              )}
              {link.dropdown && openDropdown === link.label && (
                <div className="nav-popover">
                  {link.dropdown.map((item) => (
                    <a href={`#${item.toLowerCase().replaceAll(" ", "-")}`} key={item}>
                      {item}
                      <ArrowUpRight size={13} />
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
          <span className="nav-rule" aria-hidden="true" />
          <a className="nav-link nav-login" href="#login">
            Log in
          </a>
          <a className="nav-signup" href="#signup">
            Sign up
          </a>
        </nav>

        <button
          className="mobile-menu-button"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {menuOpen && (
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {navLinks.map((link) => (
            <a key={link.label} href={link.href} onClick={() => setMenuOpen(false)}>
              {link.label}
              <ArrowUpRight size={15} />
            </a>
          ))}
          <span className="mobile-nav-rule" />
          <a href="#login" onClick={() => setMenuOpen(false)}>
            Log in <ArrowUpRight size={15} />
          </a>
          <a className="mobile-signup" href="#signup" onClick={() => setMenuOpen(false)}>
            Sign up <ArrowUpRight size={15} />
          </a>
        </nav>
      )}
    </header>
  );
}

function FigureGraphic({ type }: { type: "purpose" | "agents" | "speed" }) {
  if (type === "purpose") {
    return (
      <svg className="figure-svg" viewBox="0 0 420 300" role="img" aria-label="Stacked purpose-built system diagram">
        <g fill="none" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round">
          <path d="M101 115 211 57l111 58-111 59Z" />
          <path d="M101 115v36l110 59 111-59v-36M101 151l110 59 111-59" />
          <path d="M101 151v30l110 58 111-58v-30M101 181l110 58 111-58" opacity=".8" />
          <path d="M101 181v29l110 59 111-59v-29M101 210l110 59 111-59" opacity=".62" />
          <path d="M101 210v28l110 59 111-59v-28M101 238l110 59 111-59" opacity=".42" />
          <path d="M140 102c2-26 34-42 71-42s69 16 71 42c0 8-1 11-4 15H144c-3-4-4-7-4-15Z" />
          <path d="M143 121h136M154 132h114M174 143h75" opacity=".72" />
          <path d="m211 57 0 59M101 115l0 35M322 115l0 35" opacity=".35" strokeDasharray="3 5" />
        </g>
      </svg>
    );
  }
  if (type === "agents") {
    return (
      <svg className="figure-svg" viewBox="0 0 420 300" role="img" aria-label="Orbiting agents system diagram">
        <g fill="#0c0e10" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round">
          <path d="m93 112 57-31 60 31-58 32Z" /><path d="M93 112v76l59 32v-76Z" /><path d="m210 112-58 32v76l58-32Z" />
          <path d="m192 73 56-31 59 31-57 32Z" /><path d="M192 73v56l58 31V104Z" /><path d="m307 73-57 31v56l57-31Z" />
          <path d="m242 135 57-31 60 31-58 32Z" /><path d="M242 135v66l59 31v-65Z" /><path d="m359 135-58 32v65l58-32Z" />
          <path d="m172 223 57-31 59 31-57 32Z" /><path d="M172 223v46l59 31v-46Z" /><path d="m288 223-57 32v46l57-32Z" />
        </g>
        <g fill="none" stroke="currentColor" strokeWidth=".8" opacity=".8"><path d="m131 104 19-10 21 10-20 10Z" /><path d="m230 65 18-10 20 10-19 10Z" /><path d="m281 127 18-10 21 10-20 10Z" /><path d="m212 214 18-10 20 10-19 10Z" /></g>
      </svg>
    );
  }
  return (
    <svg className="figure-svg" viewBox="0 0 420 300" role="img" aria-label="Kinetic speed system diagram">
      <g fill="none" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round">
        <path d="m100 214 112-61 126 67-113 59Z" />
        <path d="m110 202 112-61 116 62-112 60Z" opacity=".75" />
        <path d="m120 190 111-61 107 57-108 59Z" opacity=".68" />
        <path d="m130 176 111-60 97 52-107 58Z" opacity=".6" />
        <path d="m141 162 111-60 86 47-105 57Z" opacity=".52" />
        <path d="m153 147 110-59 74 40-104 57Z" opacity=".45" />
        <path d="m166 132 107-58 61 33-99 54Z" opacity=".38" />
        <path d="m179 117 102-55 48 26-94 51Z" opacity=".3" />
        <path d="m107 216 0 12M117 204v14M128 191v15M140 177v15M152 161v16M166 147v15M180 132v14" opacity=".45" strokeDasharray="3 4" />
      </g>
    </svg>
  );
}

function ProductCanvas() {
  return (
    <div className="product-canvas" aria-label="Linear product interface preview">
      <div className="canvas-glow" />
      <div className="canvas-window">
        <aside className="canvas-sidebar">
          <div className="canvas-team"><LinearMark /><span>Linear</span><ChevronDown size={11} /></div>
          <div className="canvas-search"><Search size={12} /><span>Search</span><kbd>⌘ K</kbd></div>
          <div className="canvas-nav-group">
            <span className="canvas-nav-label">Workspace</span>
            <span className="canvas-nav-active"><Inbox size={12} />Inbox <i>4</i></span>
            <span><Layers3 size={12} />Projects</span>
            <span><Sparkles size={12} />Agent tasks</span>
          </div>
          <div className="canvas-nav-group canvas-bottom-group">
            <span className="canvas-nav-label">Favorites</span>
            <span><span className="tiny-dot dot-orange" />Faster app launch</span>
            <span><span className="tiny-dot dot-purple" />UI Refresh</span>
          </div>
        </aside>
        <div className="canvas-main">
          <div className="canvas-toolbar">
            <div className="toolbar-title"><span className="toolbar-kicker">My issues</span><span className="toolbar-count">24</span></div>
            <div className="toolbar-actions"><button><Plus size={13} /></button><button><MoreHorizontal size={14} /></button></div>
          </div>
          <div className="canvas-tabs"><span className="active">All issues</span><span>Assigned to me</span><span>Recently updated</span></div>
          <div className="issue-list">
            {[
              ["ENG-2498", "Replace isFullySynced with a sync status", "Performance", "Oct 9"],
              ["ENG-2380", "Show a stale data banner while syncing", "Reliability", "Oct 9"],
              ["ENG-2039", "Pass sync status to the dashboard", "Bug", "Oct 8"],
              ["ENG-1882", "Optimize load times", "Performance", "Oct 7"],
            ].map(([id, title, tag, date], index) => (
              <div className={`issue-row ${index === 0 ? "selected" : ""}`} key={id}>
                <span className="issue-checkbox" />
                <span className="issue-id">{id}</span>
                <span className="issue-title">{title}</span>
                <span className={`issue-tag tag-${index}`}>{tag}</span>
                <span className="issue-date">{date}</span>
              </div>
            ))}
          </div>
          <div className="canvas-cursor" />
        </div>
        <aside className="canvas-detail">
          <div className="detail-top"><span>ENG-2498</span><MoreHorizontal size={14} /></div>
          <h3>Replace isFullySynced with a sync status</h3>
          <p>Render UI before vehicle state sync when minimum required state is present.</p>
          <div className="detail-divider" />
          <div className="detail-meta"><span>Status</span><strong><i className="status-pulse" /> In progress</strong></div>
          <div className="detail-meta"><span>Priority</span><strong>Medium</strong></div>
          <div className="detail-meta"><span>Assignee</span><strong><span className="avatar avatar-orange">K</span> Karri</strong></div>
          <div className="detail-divider" />
          <div className="detail-activity"><span className="activity-dot" /><span>Linear connected by Jori</span><small>2m</small></div>
          <div className="detail-activity"><span className="activity-dot" /><span>Draft PR awaiting review</span><small>2m</small></div>
        </aside>
      </div>
      <div className="canvas-image-layer"><img src={heroImage} alt="" aria-hidden="true" /></div>
      <div className="scan-line" />
    </div>
  );
}

function FeatureMockup({ kind }: { kind: "intake" | "ai" | "plan" }) {
  if (kind === "intake") {
    return (
      <div className="feature-mockup intake-mockup" aria-label="Issues intake preview">
        <div className="mini-window-head"><span className="window-dots"><i /><i /><i /></span><span>Inbox / New requests</span><MoreHorizontal size={14} /></div>
        <div className="intake-body">
          <div className="intake-inbox">
            <span className="mini-label">Backlog <b>8</b></span>
            {intakeIssues.slice(0, 4).map(([id, title]) => (
              <div className="mini-issue" key={id}><span className="mini-check" /><b>{id}</b><span>{title}</span></div>
            ))}
            <span className="mini-label todo-label">Todo <b>71</b></span>
            <div className="mini-issue selected"><span className="mini-check" /><b>ENG-0926</b><span>Remove UI inconsistencies</span></div>
          </div>
          <div className="intake-detail">
            <span className="detail-label">ENG-0926 · Bug</span>
            <h4>Remove UI inconsistencies</h4>
            <p>Keep interfaces calm and predictable across every workspace and surface.</p>
            <div className="detail-chip-row"><span>Bug</span><span>Design</span></div>
            <div className="intake-progress"><span /><span /><span /><span /><span /></div>
          </div>
        </div>
      </div>
    );
  }
  if (kind === "ai") {
    return (
      <div className="feature-mockup ai-mockup" aria-label="Linear agent preview">
        <div className="mini-window-head"><span className="window-dots"><i /><i /><i /></span><span><Sparkles size={12} /> Linear Agent</span><span className="agent-ready">Ready</span></div>
        <div className="ai-body">
          <div className="ai-message"><span className="ai-avatar"><Sparkles size={13} /></span><div><b>Linear Agent</b><p>I've grouped the incoming issues by team and drafted a prioritized plan for review.</p></div></div>
          <div className="ai-plan-card"><div className="plan-card-title"><span className="plan-icon"><Command size={13} /></span><span>Q4 mobile reliability</span><span className="plan-status">Draft</span></div><div className="plan-card-line" /><div className="plan-card-line short" /><div className="plan-card-line shorter" /><div className="plan-card-footer"><span>12 issues</span><span>3 projects</span><span>Open plan <ArrowRight size={12} /></span></div></div>
          <div className="ai-input"><span>Ask Linear Agent anything...</span><CornerDownRight size={14} /></div>
        </div>
      </div>
    );
  }
  return (
    <div className="feature-mockup plan-mockup" aria-label="Project planning preview">
      <div className="mini-window-head"><span className="window-dots"><i /><i /><i /></span><span>Project / Mobile launch</span><button>Share <ArrowUpRight size={12} /></button></div>
      <div className="plan-body"><div className="plan-sidebar"><span className="mini-label">Project overview</span><span className="plan-side-active">Overview</span><span>Updates</span><span>Issues</span><span>Documents</span></div><div className="plan-main"><span className="detail-label">PROJECT · IN PROGRESS</span><h4>Mobile launch</h4><p>A focused workspace for planning, building, and shipping the next release.</p><div className="plan-progress-track"><span /><b>64%</b></div><div className="plan-sections"><span><i className="plan-dot green" />On track <b>18</b></span><span><i className="plan-dot amber" />In review <b>6</b></span><span><i className="plan-dot gray" />Todo <b>12</b></span></div></div></div>
    </div>
  );
}

function BuildReviewBoard() {
  const diffLines = [
    ["01", "import React from 'react'", "import React from 'react'", ""],
    ["02", "import { View, ActivityIndicator } from 'react-native'", "import { View, ActivityIndicator } from 'react-native'", ""],
    ["03", "import { useVehicleState } from '@hooks/useVehicleState'", "import { useVehicleState, SyncStatus }", "added"],
    ["04", "import { Dashboard } from '@components/Dashboard'", "import { Dashboard } from '@components/Dashboard'", ""],
    ["05", "", "", ""],
    ["06", "export const HomeScreen = () => {", "export const HomeScreen = () => {", ""],
    ["07", "  const { vehicleState, isFullySynced } = useVehicleState()", "  const { vehicleState, syncStatus } = useVehicleState()", "changed"],
    ["08", "", "", ""],
    ["09", "  if (!isFullySynced) {", "  if (syncStatus === SyncStatus.Syncing) {", "changed"],
    ["10", "    return <ActivityIndicator size=\"large\" />", "    return <ActivityIndicator size=\"large\" />", ""],
    ["11", "  }", "  }", ""],
    ["12", "", "", ""],
    ["13", "  return (", "  return (", ""],
    ["14", "    <View>", "    <View>", ""],
    ["15", "      <Dashboard state={vehicleState} />", "      <Dashboard state={vehicleState} />", ""],
    ["16", "    </View>", "    </View>", ""],
    ["17", "  )", "  )", ""],
    ["18", "}", "}", ""],
  ];

  return (
    <div className="build-review-board" aria-label="Code review board with issue sidebar and diff viewer">
      <aside className="review-sidebar">
        <div className="review-sidebar-head"><span className="sidebar-chevron">⌄</span><span className="review-status-dot" /> <b>In Review</b><small>3</small></div>
        {["ENG-2498  Replace isFullySynced with a sync status", "ENG-2380  Show a stale data banner while syncing", "ENG-2039  Pass sync status to the dashboard"].map((issue, index) => <div className={`review-issue ${index === 0 ? "review-active" : ""}`} key={issue}><span className="issue-signal">▥</span><span>{issue}</span></div>)}
        <div className="review-sidebar-head progress-head"><span className="sidebar-chevron">⌄</span><span className="review-status-dot status-amber" /> <b>In Progress</b><small>4</small></div>
        {["ENG-2076  Reduce ETA jitter", "ENG-2108  Handle GPS dropouts gracefully", "ENG-2143  Optimize map tile loading on initial app open", "ENG-2187  Prevent duplicate ride requests on poor network"].map((issue) => <div className="review-issue" key={issue}><span className="issue-signal signal-amber">▥</span><span>{issue}</span></div>)}
        <div className="review-sidebar-head todo-head"><span className="sidebar-chevron">⌄</span><span className="review-status-dot status-gray" /> <b>Todo</b><small>4</small></div>
        {["ENG-2254  Reduce unnecessary map re-rendering on handoff", "ENG-2291  Clean up deprecated APIs used by the rider", "ENG-2327  Speed up CI pipelines for mobile builds"].map((issue) => <div className="review-issue muted-issue" key={issue}><span className="issue-signal signal-gray">▥</span><span>{issue}</span></div>)}
      </aside>
      <div className="diff-window">
        <div className="diff-window-bar"><span className="file-icon">◧</span><span className="file-path">kinetic-ios/src/screens/Home/HomeScreen.tsx</span><span className="diff-branch">Linear <ChevronDown size={11} /></span></div>
        <div className="diff-editor-head"><span>←</span><span>Changes</span><span className="diff-count">2 files</span><span className="editor-action">⋯</span></div>
        <div className="diff-columns"><span>HEAD</span><span>CHANGES</span></div>
        <div className="diff-code">
          {diffLines.map(([lineNo, oldLine, newLine, state]) => <div className={`diff-line ${state}`} key={lineNo}><span className="line-number">{lineNo}</span><span className="code-cell old-code">{oldLine}</span><span className="code-cell new-code">{newLine}</span></div>)}
        </div>
        <div className="diff-cursor" />
      </div>
    </div>
  );
}

function PlanningBoard() {
  const dotColumns = [
    { x: 90, ys: [168, 187, 204, 221, 238, 258, 278, 297, 318, 339], tone: "cyan" },
    { x: 220, ys: [191, 211, 230, 249, 267, 286, 305, 323], tone: "cyan" },
    { x: 350, ys: [147, 163, 181, 201, 220, 240, 259, 279, 299, 318], tone: "cyan" },
    { x: 480, ys: [174, 191, 212, 232, 252, 272, 294, 313], tone: "cyan" },
  ];

  return (
    <div className="planning-board" aria-label="Timeline and cycle time by agent chart">
      <div className="gantt-panel">
        <div className="gantt-months"><span />{["9", "16", "23", "6", "13", "20", "27", "4", "11", "18", "25", "1", "8", "15", "22", "M"].map((day, index) => <span key={`${day}-${index}`}>{day}</span>)}</div>
        <div className="gantt-month-names"><span>MAR</span><span>APR</span><span>MAY</span></div>
        <div className="gantt-grid-lines"><i /><i /><i /><i /><i /><i /><i /><i /></div>
        <div className="gantt-row row-ui"><div className="gantt-row-label"><span className="project-symbol symbol-blue">✣</span> UI Refresh <b>↗</b></div><div className="gantt-bar"><span>Core screens</span></div><span className="gantt-milestone milestone-pink">⌄</span><span className="gantt-milestone-label">Polish</span></div>
        <div className="gantt-row row-spilt"><div className="gantt-row-label"><span className="project-symbol symbol-green">▣</span> Split fares <b>↗</b></div><div className="gantt-bar"><span>Internal</span></div><span className="gantt-milestone milestone-white">◆</span></div>
        <div className="gantt-row row-telemetry"><div className="gantt-row-label"><span className="project-symbol symbol-purple">◌</span> Telemetry reliability <b>↗</b></div><div className="gantt-bar telemetry-bar"><span /></div><span className="gantt-milestone milestone-white">◆</span><span className="telemetry-day">02</span></div>
      </div>
      <div className="cycle-panel">
        <div className="cycle-title">Cycle time by agent</div>
        <svg className="cycle-chart" viewBox="0 0 550 420" role="img" aria-label="Cycle time trends from October to December 2025">
          <g className="chart-guides"><path d="M0 92H550M0 195H550M0 297H550" /><path d="M112 0V360M280 0V360M442 0V360" /></g>
          <path className="trend-line trend-pink" d="M0 137h76l18-24h86l24 0 18 38h65l20 45h58l24-15h92l20 18h69" />
          <path className="trend-line trend-amber" d="M0 184h76l18 22h86l24 0 18-29h65l20 20h58l24 47h92l20-8h69" />
          {dotColumns.map((column, colIndex) => column.ys.map((y, dotIndex) => <circle key={`${colIndex}-${dotIndex}`} className={`chart-dot ${column.tone}`} cx={column.x + ((dotIndex % 3) - 1) * 10} cy={y + (dotIndex % 2) * 4} r={dotIndex % 4 === 0 ? 3 : 2.25} style={{ "--dot-delay": `${(colIndex * 7 + dotIndex) * 55}ms` } as CSSProperties} />))}
          <g className="chart-axis"><text x="48" y="396">Oct 2025</text><text x="206" y="396">Nov 2025</text><text x="374" y="396">Dec 2025</text></g>
        </svg>
      </div>
      <div className="planning-scan" />
    </div>
  );
}

export default function Home() {
  const heroReveal = useReveal<HTMLDivElement>();
  const figureReveal = useReveal<HTMLDivElement>();
  const intakeReveal = useReveal<HTMLDivElement>();
  const aiReveal = useReveal<HTMLDivElement>();
  const planReveal = useReveal<HTMLDivElement>();

  return (
    <div className="linear-page" id="top">
      <Nav />

      <main>
        <section className="hero-section" aria-labelledby="hero-title">
          <div className="hero-orbit orbit-one" />
          <div className="hero-orbit orbit-two" />
          <div className="hero-content shell">
            <div className="eyebrow"><span className="eyebrow-line" />PRODUCT DEVELOPMENT SYSTEM <span className="eyebrow-code">01 — 26</span></div>
            <div className="hero-copy reveal-on-load" ref={heroReveal.ref} data-visible={heroReveal.visible}>
              <h1 id="hero-title">The product development <em>system</em> for teams and agents.</h1>
              <p>Purpose-built for planning and building products. Designed for the AI era.</p>
              <div className="hero-actions"><a className="primary-button" href="#signup">Get started <ArrowRight size={15} /></a><a className="text-button" href="#product">Explore the system <ArrowUpRight size={15} /></a></div>
            </div>
            <div className="hero-meta"><span>SCROLL TO EXPLORE</span><span className="hero-meta-rule" /><span>01 / 08</span></div>
          </div>
          <div className="hero-product-wrap"><ProductCanvas /></div>
        </section>

        <section className="logo-strip" aria-label="Teams building the future">
          <div className="shell logo-strip-inner"><span className="strip-label">POWERING THE TEAMS BUILDING THE FUTURE</span><div className="customer-marks"><span>Vercel</span><span>ramp</span><span>OpenAI</span><span>descript</span><span>coinbase</span><span>Webflow</span></div></div>
        </section>

        <section className="figures-section section-dark" id="product" aria-labelledby="figures-title">
          <div className="shell">
            <div className="section-intro reveal-on-load" ref={figureReveal.ref} data-visible={figureReveal.visible}>
              <span className="section-kicker">THE SYSTEM, AT ITS CORE</span>
              <h2 id="figures-title">A new species of product tool.</h2>
              <p>Purpose-built for modern teams with AI workflows at their core, Linear sets a new standard for planning and building products.</p>
            </div>
            <div className="figure-grid">
              {figures.map((figure, index) => (
                <article className="figure-card" key={figure.index} style={{ "--figure-delay": `${index * 90}ms` } as CSSProperties}>
                  <div className="figure-label">{figure.index}</div>
                  <div className="figure-visual"><FigureGraphic type={index === 0 ? "purpose" : index === 1 ? "agents" : "speed"} /><img className="figure-generated-layer" src={figure.image} alt="" aria-hidden="true" /><div className="visual-sheen" /></div>
                  <h3>{figure.title}</h3>
                  <p>{figure.copy}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="feature-section intake-section" id="intake" aria-labelledby="intake-title">
          <div className="shell feature-layout">
            <div className="feature-copy reveal-on-load" ref={intakeReveal.ref} data-visible={intakeReveal.visible}><span className="section-kicker">01 / INTAKE</span><h2 id="intake-title">Turn every conversation into action.</h2><p>Automatically turn conversations and customer feedback into actionable issues that are instantly routed, labeled, and prioritized for the right team.</p><a className="feature-link" href="#now">Learn more <ArrowRight size={14} /></a></div>
            <FeatureMockup kind="intake" />
          </div>
        </section>

        <section className="feature-section ai-section" id="ai" aria-labelledby="ai-title">
          <div className="shell feature-layout feature-layout-reverse">
            <FeatureMockup kind="ai" />
            <div className="feature-copy reveal-on-load" ref={aiReveal.ref} data-visible={aiReveal.visible}><span className="section-kicker">02 / AI</span><h2 id="ai-title">Agents that move work forward.</h2><p>Linear Agent understands your team's context, coordinates the details, and handles the work between an idea and a shipped product.</p><a className="feature-link" href="#agents">Meet Linear Agent <ArrowRight size={14} /></a></div>
          </div>
        </section>

        <section className="feature-section plan-section" id="plan" aria-labelledby="plan-title">
          <div className="shell feature-layout">
            <div className="feature-copy reveal-on-load" ref={planReveal.ref} data-visible={planReveal.visible}><span className="section-kicker">03 / PLAN</span><h2 id="plan-title">Clarity from first thought to final ship.</h2><p>Projects, documents, and issues stay connected in one focused workspace, so teams always know what matters next.</p><a className="feature-link" href="#projects">Explore planning <ArrowRight size={14} /></a></div>
            <FeatureMockup kind="plan" />
          </div>
        </section>

        <section className="planning-monitor-section" id="planning" aria-labelledby="planning-title">
          <div className="shell planning-header">
            <div className="planning-heading"><span className="section-kicker">04 / PLAN</span><h2 id="planning-title">Planning<br />and monitoring</h2></div>
            <div className="planning-description"><p>Plan and navigate from idea to launch. Align your team with product initiatives, strategic roadmaps, and clear, up-to-date PRDs.</p><a className="feature-link" href="#projects">Learn more <ArrowRight size={14} /></a></div>
          </div>
          <div className="shell planning-board-wrap"><PlanningBoard /></div>
        </section>

        <section className="build-review-section" id="build" aria-labelledby="build-title">
          <div className="shell build-header">
            <div className="build-heading"><span className="section-kicker">05 / BUILD</span><h2 id="build-title">Build, review,<br />and ship</h2></div>
            <div className="build-description"><p>Streamline code reviews with clear diffs, better context, and fewer back-and-forth comments. Keep PRs moving without sacrificing quality.</p><a className="feature-link" href="#projects">Learn more <ArrowRight size={14} /></a></div>
          </div>
          <div className="shell build-board-wrap"><BuildReviewBoard /></div>
        </section>

        <section className="statement-section" id="customers">
          <div className="statement-grid shell"><span className="section-kicker">THE LINEAR WAY</span><h2>Designed for teams that care about the details.</h2><p>When the system gets out of the way, thoughtful teams find the momentum to build products people love.</p><a className="primary-button" href="#signup">See Linear in action <Play size={14} fill="currentColor" /></a></div>
          <div className="statement-rule statement-rule-a" /><div className="statement-rule statement-rule-b" />
        </section>

        <section className="footer-cta" id="signup"><div className="shell footer-cta-inner"><div><span className="section-kicker">START WITH MOMENTUM</span><h2>Make product development feel <em>inevitable.</em></h2></div><a className="primary-button primary-button-light" href="#contact">Get started <ArrowRight size={15} /></a></div></section>
      </main>

      <footer className="site-footer" id="contact">
        <div className="shell footer-grid">
          <div className="footer-brand"><a className="wordmark footer-wordmark" href="#top"><LinearMark /><span>Linear</span></a><p>Linear is a purpose-built tool for planning and building products.</p><span className="footer-fine">© 2026 Linear Orbit, Inc.</span></div>
          <div className="footer-links"><div><span>Product</span><a href="#intake">Intake</a><a href="#plan">Plan</a><a href="#ai">AI</a><a href="#build">Build</a></div><div><span>Resources</span><a href="#customers">Customers</a><a href="#now">Now</a><a href="#contact">Contact</a><a href="#pricing">Pricing</a></div><div><span>Connect</span><a href="#login">Log in</a><a href="#signup">Sign up</a><a href="#contact">Twitter / X</a><a href="#contact">Security</a></div></div>
        </div>
        <div className="shell footer-bottom"><span>Built for focus.</span><span className="footer-bottom-right">System status <i className="status-pulse" /> All systems operational</span></div>
      </footer>
    </div>
  );
}
