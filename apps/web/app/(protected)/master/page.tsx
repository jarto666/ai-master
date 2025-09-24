"use client";

import { useState } from "react";
import { useAuth } from "../../hooks/useAuth";

export default function MasterPage() {
  const { data: user, isLoading, error, logout } = useAuth();

  const [fileKey, setFileKey] = useState<string>("");
  const [fileType, setFileType] = useState<string>("audio/wav");
  const [fileSize, setFileSize] = useState<number>(1234);
  const [uploadType, setUploadType] = useState<string>("test");
  const [status, setStatus] = useState<string>("idle");

  async function callPresign() {
    const res = await fetch("/api/uploads/presign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        file_name: fileKey || "test.wav",
        file_type: fileType,
        file_size: fileSize,
        upload_type: uploadType,
      }),
    });
    const json = await res.json();
    setStatus(`presign ${res.status}: ${JSON.stringify(json)}`);
  }

  return (
    <div className="grid grid-rows-[auto_1fr] min-h-screen">
      <header className="flex items-center justify-between px-6 py-4 border-b">
        <div className="text-sm opacity-80">
          {isLoading
            ? "loading..."
            : `user: ${user?.name ?? ""} <${user?.email ?? ""}>`}
        </div>
        <button
          className="px-3 py-2 rounded bg-zinc-700 text-white"
          onClick={() => logout()}
        >
          Logout
        </button>
      </header>
      <main className="flex flex-col gap-4 items-stretch w-full max-w-xl mx-auto p-8">
        <h1 className="text-2xl font-semibold">Presign upload</h1>
        <div className="mt-2 grid gap-2">
          <label className="text-sm">file name</label>
          <input
            className="border px-2 py-1"
            value={fileKey}
            onChange={(e) => setFileKey(e.target.value)}
            placeholder="test.wav"
          />
          <label className="text-sm">file type</label>
          <input
            className="border px-2 py-1"
            value={fileType}
            onChange={(e) => setFileType(e.target.value)}
          />
          <label className="text-sm">file size</label>
          <input
            className="border px-2 py-1"
            value={fileSize}
            onChange={(e) => setFileSize(Number(e.target.value))}
          />
          <label className="text-sm">upload type</label>
          <input
            className="border px-2 py-1"
            value={uploadType}
            onChange={(e) => setUploadType(e.target.value)}
          />
          <button
            className="mt-2 px-3 py-2 rounded bg-blue-600 text-white"
            onClick={callPresign}
          >
            Call /uploads/presign
          </button>
        </div>
        <div className="mt-6 text-sm">status: {status}</div>
        {error ? <div className="text-sm text-red-600">auth error</div> : null}
      </main>
    </div>
  );
}
