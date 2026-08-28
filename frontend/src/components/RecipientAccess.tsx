import React, { useEffect, useState } from "react";
import { accessFile, AccessResult } from "../api/client";

interface RecipientAccessProps {
  fileId: string;
  token: string;
}

export const RecipientAccess: React.FC<RecipientAccessProps> = ({ fileId, token }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AccessResult | null>(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await accessFile(fileId, token);
        setData(res);
      } catch (err: any) {
        setError(err.message || "Unable to access or download file. It may have expired or been deleted.");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [fileId, token]);

  if (isLoading) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "3rem 2rem" }}>
        <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>⏳</div>
        <h2 style={{ fontSize: "1.25rem", color: "#1e293b" }}>Verifying access link...</h2>
        <p style={{ color: "#64748b", marginTop: "0.5rem" }}>Checking token signature and preparing your secure download.</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "3rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🚫</div>
        <h2 style={{ fontSize: "1.5rem", color: "#b91c1c", marginBottom: "0.5rem" }}>Access Unavailable</h2>
        <p style={{ color: "#64748b", maxWidth: "450px", margin: "0 auto 1.5rem" }}>
          {error || "This download link is invalid or the file has already completed its lifecycle and was automatically deleted."}
        </p>
        <a href="/" className="btn btn-secondary">
          Go to CloudShare Home
        </a>
      </div>
    );
  }

  return (
    <div className="card" style={{ textAlign: "center", padding: "2.5rem 2rem" }}>
      <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>📦</div>
      <h2 style={{ fontSize: "1.5rem", color: "#0f172a", marginBottom: "0.5rem" }}>Your File is Ready!</h2>
      <p style={{ color: "#64748b", marginBottom: "1.5rem" }}>
        Logged access for <strong>{data.recipient_email}</strong>
      </p>

      <div style={{ backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", padding: "1.25rem", borderRadius: "8px", marginBottom: "2rem", maxWidth: "400px", margin: "0 auto 2rem" }}>
        <p style={{ fontSize: "1.1rem", fontWeight: 600, color: "#1e293b" }}>{data.original_filename}</p>
        <p style={{ fontSize: "0.85rem", color: "#64748b", marginTop: "0.25rem" }}>
          {(data.size_bytes / 1024).toFixed(1)} KB • {data.content_type}
        </p>
      </div>

      <a
        href={data.download_url}
        download={data.original_filename}
        className="btn btn-primary"
        style={{ padding: "0.9rem 2rem", fontSize: "1.1rem" }}
      >
        ⬇️ Download File Directly
      </a>

      <p style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "1.5rem" }}>
        🔒 Direct, encrypted download generated via AWS S3 Presigned URL.
      </p>
    </div>
  );
};
