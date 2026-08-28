import React from "react";

export const Header: React.FC = () => {
  return (
    <header style={{ backgroundColor: "#ffffff", borderBottom: "1px solid #e2e8f0", padding: "1rem 0" }}>
      <div className="container" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ backgroundColor: "#2563eb", color: "#ffffff", padding: "0.5rem", borderRadius: "8px", fontWeight: "bold" }}>
            ☁️
          </div>
          <div>
            <h1 style={{ fontSize: "1.25rem", fontWeight: "bold", color: "#0f172a" }}>CloudShare Secure</h1>
            <p style={{ fontSize: "0.8rem", color: "#64748b" }}>Completion-based auto-deleting cloud file sharing</p>
          </div>
        </div>
        <div>
          <a href="/" className="btn btn-secondary" style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}>
            New Share
          </a>
        </div>
      </div>
    </header>
  );
};
