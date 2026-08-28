import React, { useState, useEffect } from "react";
import { Header } from "./components/Header";
import { UploadForm } from "./components/UploadForm";
import { RecipientAccess } from "./components/RecipientAccess";

export const App: React.FC = () => {
  const [accessParams, setAccessParams] = useState<{ fileId: string; token: string } | null>(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const fileId = urlParams.get("file_id") || urlParams.get("fileId");
    const token = urlParams.get("token");

    // Also check pathname: /files/:fileId/access?token=...
    const pathMatch = window.location.pathname.match(/\/files\/([^\/]+)\/access/);
    const pathFileId = pathMatch ? pathMatch[1] : null;

    const resolvedFileId = fileId || pathFileId;
    if (resolvedFileId && token) {
      setAccessParams({ fileId: resolvedFileId, token });
    }
  }, []);

  return (
    <>
      <Header />
      <main className="container">
        {accessParams ? (
          <RecipientAccess fileId={accessParams.fileId} token={accessParams.token} />
        ) : (
          <UploadForm />
        )}
      </main>
    </>
  );
};

export default App;
