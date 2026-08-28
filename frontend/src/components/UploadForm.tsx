import React, { useState } from "react";
import { uploadFile, UploadResult } from "../api/client";

export const UploadForm: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [recipients, setRecipients] = useState<string[]>([""]);
  const [uploaderEmail, setUploaderEmail] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);

  const handleAddRecipient = () => {
    setRecipients([...recipients, ""]);
  };

  const handleRemoveRecipient = (index: number) => {
    if (recipients.length > 1) {
      setRecipients(recipients.filter((_, i) => i !== index));
    }
  };

  const handleRecipientChange = (index: number, value: string) => {
    const updated = [...recipients];
    updated[index] = value;
    setRecipients(updated);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const validateEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!file) {
      setError("Please select a file to upload.");
      return;
    }

    const cleanedRecipients = recipients.map((r) => r.trim()).filter(Boolean);
    if (cleanedRecipients.length === 0) {
      setError("At least one recipient email address is required.");
      return;
    }

    for (const email of cleanedRecipients) {
      if (!validateEmail(email)) {
        setError(`Invalid email address format: "${email}"`);
        return;
      }
    }

    setIsUploading(true);
    try {
      const res = await uploadFile(file, cleanedRecipients, uploaderEmail.trim() || undefined);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during upload.");
    } finally {
      setIsUploading(false);
    }
  };

  const copyToClipboard = (email: string, link: string) => {
    navigator.clipboard.writeText(link);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2500);
  };

  if (result) {
    return (
      <div className="card">
        <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>🎉</div>
          <h2 style={{ fontSize: "1.5rem", color: "#166534" }}>File Uploaded & Encrypted!</h2>
          <p style={{ color: "#64748b", marginTop: "0.25rem" }}>
            <strong>{result.original_filename}</strong> ({(result.size_bytes / 1024).toFixed(1)} KB)
          </p>
        </div>

        <div style={{ backgroundColor: "#eff6ff", border: "1px solid #bfdbfe", padding: "1rem", borderRadius: "8px", marginBottom: "1.5rem" }}>
          <h3 style={{ fontSize: "1rem", color: "#1e40af", marginBottom: "0.5rem" }}>⚡ Auto-Deletion Rule</h3>
          <p style={{ fontSize: "0.875rem", color: "#1e3a8a" }}>
            This file will be automatically destroyed from Amazon S3 and DynamoDB once all {result.recipients.length} recipients have downloaded their copy.
          </p>
        </div>

        <h3 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Unique Recipient Access Links</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.5rem" }}>
          {Object.entries(result.recipient_links).map(([email, link]) => (
            <div key={email} style={{ padding: "0.75rem", border: "1px solid #e2e8f0", borderRadius: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ overflow: "hidden", textOverflow: "ellipsis", marginRight: "1rem" }}>
                <span style={{ fontWeight: 600, display: "block", fontSize: "0.9rem" }}>{email}</span>
                <span style={{ fontSize: "0.8rem", color: "#64748b", wordBreak: "break-all" }}>{link}</span>
              </div>
              <button
                className="btn btn-secondary"
                style={{ fontSize: "0.8rem", padding: "0.4rem 0.8rem", whiteSpace: "nowrap" }}
                onClick={() => copyToClipboard(email, link)}
              >
                {copiedEmail === email ? "Copied! ✓" : "Copy Link"}
              </button>
            </div>
          ))}
        </div>

        <button
          className="btn btn-primary"
          style={{ width: "100%" }}
          onClick={() => {
            setResult(null);
            setFile(null);
            setRecipients([""]);
          }}
        >
          Share Another File
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 style={{ fontSize: "1.5rem", marginBottom: "0.5rem", color: "#0f172a" }}>Share a File Securely</h2>
      <p style={{ color: "#64748b", marginBottom: "1.5rem" }}>
        Upload a file and assign recipients. Once everyone downloads it, the file self-destructs.
      </p>

      {error && (
        <div style={{ backgroundColor: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", padding: "0.75rem 1rem", borderRadius: "8px", marginBottom: "1.5rem" }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "0.5rem", fontSize: "0.9rem" }}>
            Select File
          </label>
          <input
            type="file"
            className="input"
            onChange={handleFileChange}
            disabled={isUploading}
          />
          {file && (
            <p style={{ fontSize: "0.85rem", color: "#166534", marginTop: "0.5rem" }}>
              Selected: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
            </p>
          )}
        </div>

        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "0.5rem", fontSize: "0.9rem" }}>
            Your Email (Optional)
          </label>
          <input
            type="email"
            placeholder="you@company.com"
            className="input"
            value={uploaderEmail}
            onChange={(e) => setUploaderEmail(e.target.value)}
            disabled={isUploading}
          />
        </div>

        <div style={{ marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
            <label style={{ fontWeight: 600, fontSize: "0.9rem" }}>
              Recipient Emails (Required)
            </label>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.8rem", padding: "0.25rem 0.6rem" }}
              onClick={handleAddRecipient}
              disabled={isUploading}
            >
              + Add Recipient
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {recipients.map((recipient, idx) => (
              <div key={idx} style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  type="email"
                  placeholder={`recipient${idx + 1}@example.com`}
                  className="input"
                  value={recipient}
                  onChange={(e) => handleRecipientChange(idx, e.target.value)}
                  disabled={isUploading}
                  required
                />
                {recipients.length > 1 && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ color: "#ef4444", padding: "0.5rem 0.75rem" }}
                    onClick={() => handleRemoveRecipient(idx)}
                    disabled={isUploading}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: "100%", padding: "1rem" }}
          disabled={isUploading}
        >
          {isUploading ? "Uploading & Encrypting..." : "Upload & Send Secure Links"}
        </button>
      </form>
    </div>
  );
};
