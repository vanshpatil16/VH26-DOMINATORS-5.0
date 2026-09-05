import { useLocation } from "wouter";
import { ArrowLeft, Terminal } from "lucide-react";

export default function NotFound() {
  const [, setLocation] = useLocation();

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#08090a",
        fontFamily: "'DM Sans', system-ui, sans-serif",
        padding: "24px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "440px",
          textAlign: "center",
        }}
      >
        {/* Glitch 404 */}
        <div
          style={{
            position: "relative",
            marginBottom: "32px",
          }}
        >
          <h1
            style={{
              fontSize: "120px",
              fontWeight: 600,
              letterSpacing: "-0.06em",
              lineHeight: 1,
              color: "rgba(255,255,255,0.04)",
              margin: 0,
              userSelect: "none",
            }}
          >
            404
          </h1>
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "12px",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Terminal
                style={{ width: "22px", height: "22px", color: "#555" }}
              />
            </div>
          </div>
        </div>

        {/* Copy */}
        <h2
          style={{
            fontSize: "18px",
            fontWeight: 500,
            color: "#e0e0de",
            margin: "0 0 10px",
            letterSpacing: "-0.02em",
          }}
        >
          Page not found
        </h2>
        <p
          style={{
            fontSize: "14px",
            color: "#6b6e72",
            lineHeight: 1.6,
            margin: "0 0 32px",
          }}
        >
          The page you're looking for doesn't exist or has been moved.
        </p>

        {/* Action */}
        <button
          onClick={() => setLocation("/")}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px",
            fontSize: "13px",
            fontWeight: 500,
            color: "#e0e0de",
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "8px",
            cursor: "pointer",
            transition: "all 150ms ease",
            fontFamily: "inherit",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.08)";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
          }}
        >
          <ArrowLeft style={{ width: "14px", height: "14px" }} />
          Back to home
        </button>
      </div>
    </div>
  );
}
