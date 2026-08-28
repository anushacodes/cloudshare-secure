export interface UploadResult {
  file_id: string;
  original_filename: string;
  size_bytes: number;
  content_type: string;
  uploaded_at: string;
  recipients: string[];
  s3_key: string;
  recipient_links: Record<string, string>;
}

export interface AccessResult {
  file_id: string;
  original_filename: string;
  size_bytes: number;
  content_type: string;
  download_url: string;
  recipient_email: string;
  access_recorded: boolean;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function uploadFile(
  file: File,
  recipients: string[],
  uploaderEmail: string = "user@cloudshare.local"
): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("recipients", JSON.stringify(recipients));
  formData.append("uploader_email", uploaderEmail);

  const response = await fetch(`${API_BASE}/files/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

export async function accessFile(
  fileId: string,
  token: string
): Promise<AccessResult> {
  const response = await fetch(
    `${API_BASE}/files/${encodeURIComponent(fileId)}/access?token=${encodeURIComponent(token)}`
  );

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Access failed" }));
    throw new Error(err.detail || `Access failed with status ${response.status}`);
  }

  return response.json();
}
