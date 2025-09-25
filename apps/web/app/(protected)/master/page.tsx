"use client";

import { useState } from "react";
import type { ChangeEvent } from "react";
import { useAuth } from "../../hooks/useAuth";

export default function MasterPage() {
  const { data: user, isLoading, error, logout } = useAuth();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [objectKey, setObjectKey] = useState<string | null>(null);
  const [publicBaseUrl, setPublicBaseUrl] = useState<string | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
    setStatus("idle");
    setObjectKey(null);
    setJobId(null);
    setJobStatus(null);
    setErrorText(null);
    setResultUrl(null);
    setPreviewUrl(null);
  }

  async function uploadAndStart() {
    try {
      setErrorText(null);
      setResultUrl(null);
      setPreviewUrl(null);
      if (!selectedFile) {
        setStatus("Please select a file first.");
        return;
      }

      setStatus("Creating asset...");
      const assetRes = await fetch("/api/assets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          file_name: selectedFile.name,
          file_type: selectedFile.type || "audio/wav",
          file_size: selectedFile.size,
        }),
      });
      const assetPayload = await assetRes.json();
      if (!assetRes.ok) {
        setStatus(`Create asset failed ${assetRes.status}`);
        setErrorText(
          typeof assetPayload?.detail === "string"
            ? assetPayload.detail
            : JSON.stringify(assetPayload)
        );
        return;
      }
      const asset = assetPayload.asset;
      const presign = assetPayload.upload || {};
      const assetId: string | undefined = asset?.id || asset?._id;
      const url: string = presign.url;
      const fields: Record<string, string> = presign.fields || {};
      const key = fields.key || presign.key;
      if (!url || !key) {
        setStatus("Presign response missing url/key");
        return;
      }

      setStatus("Uploading to S3...");
      const formData = new FormData();
      Object.entries(fields).forEach(([k, v]) => formData.append(k, v));
      formData.append("file", selectedFile);
      const uploadRes = await fetch(url, { method: "POST", body: formData });
      if (
        !(uploadRes.status === 204 || uploadRes.status === 201 || uploadRes.ok)
      ) {
        const text = await uploadRes.text();
        setStatus(`Upload failed ${uploadRes.status}`);
        setErrorText(text.slice(0, 500));
        return;
      }

      setObjectKey(key);
      setPublicBaseUrl(url); // typically http://localhost:9000/<bucket>
      if (!assetId) {
        setStatus("Asset id missing in response");
        return;
      }

      setStatus("Confirming upload...");
      const confirmRes = await fetch(`/api/assets/${assetId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({}),
      });
      const confirmPayload = await confirmRes.json().catch(() => ({}));
      if (!confirmRes.ok) {
        setStatus(`Confirm failed ${confirmRes.status}`);
        setErrorText(JSON.stringify(confirmPayload));
        return;
      }

      setStatus("Starting mastering...");
      const startRes = await fetch("/api/mastering/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ assetId: assetId }),
      });
      const job = await startRes.json();
      if (!startRes.ok) {
        setStatus(`Start mastering failed ${startRes.status}`);
        setErrorText(JSON.stringify(job));
        return;
      }
      const createdJobId: string | undefined = job?._id || job?.id;
      setJobId(createdJobId || null);
      setJobStatus(job?.status || "queued");
      setStatus(createdJobId ? `Job created: ${createdJobId}` : "Job created");
    } catch (e: unknown) {
      setStatus("Unexpected error");
      setErrorText(e instanceof Error ? e.message : String(e));
    }
  }

  async function checkJobStatus() {
    try {
      setErrorText(null);
      setResultUrl(null);
      setPreviewUrl(null);
      if (!jobId) {
        setStatus("No job to check. Upload and start first.");
        return;
      }
      setStatus("Checking status...");
      const res = await fetch(`/api/mastering/${jobId}`);
      const job = await res.json();
      if (!res.ok) {
        setStatus(`Status check failed ${res.status}`);
        setErrorText(JSON.stringify(job));
        return;
      }
      const st: string = job?.status;
      setJobStatus(st);
      if (st === "failed") {
        setStatus("Job failed");
        setErrorText(
          job?.last_error || job?.lastError || job?.error || "Unknown error"
        );
        return;
      }
      if (st === "done") {
        setStatus("Job done");
        const base =
          publicBaseUrl ||
          (process.env.NEXT_PUBLIC_PUBLIC_BUCKET_URL as string | undefined) ||
          "";
        const resultKey: string | undefined = job?.result_object_key;
        const previewKey: string | undefined = job?.preview_object_key;
        if (base && resultKey) setResultUrl(`${base}/${resultKey}`);
        if (base && previewKey) setPreviewUrl(`${base}/${previewKey}`);
        return;
      }
      setStatus(`Job status: ${st}`);
    } catch (e: unknown) {
      setStatus("Unexpected error");
      setErrorText(e instanceof Error ? e.message : String(e));
    }
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
        <h1 className="text-2xl font-semibold">Mastering flow</h1>
        <div className="mt-2 grid gap-2">
          <label className="text-sm">Select audio file</label>
          <input
            className="border px-2 py-1"
            type="file"
            accept="audio/*"
            onChange={onFileChange}
          />

          <button
            className="mt-2 px-3 py-2 rounded bg-blue-600 text-white"
            onClick={uploadAndStart}
          >
            Upload & Start Mastering
          </button>

          <div className="text-sm opacity-80">
            {objectKey ? `Object key: ${objectKey}` : null}
            {jobId ? ` • Job ID: ${jobId}` : null}
          </div>

          <button
            className="mt-2 px-3 py-2 rounded bg-zinc-700 text-white"
            onClick={checkJobStatus}
          >
            Check Job Status
          </button>
        </div>

        <div className="mt-6 text-sm">status: {status}</div>
        {jobStatus ? (
          <div className="text-sm">job status: {jobStatus}</div>
        ) : null}
        {errorText ? (
          <div className="text-sm text-red-600 whitespace-pre-wrap">
            {errorText}
          </div>
        ) : null}
        {previewUrl ? (
          <div className="text-sm">
            preview:{" "}
            <a
              className="underline text-blue-600"
              href={previewUrl}
              target="_blank"
              rel="noreferrer"
            >
              {previewUrl}
            </a>
          </div>
        ) : null}
        {resultUrl ? (
          <div className="text-sm">
            result:{" "}
            <a
              className="underline text-blue-600"
              href={resultUrl}
              target="_blank"
              rel="noreferrer"
            >
              {resultUrl}
            </a>
          </div>
        ) : null}
        {error ? <div className="text-sm text-red-600">auth error</div> : null}
      </main>
    </div>
  );
}
