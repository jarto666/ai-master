"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { ChangeEvent } from "react";
import { useAuth } from "../../hooks/useAuth";

export default function MasterPage() {
  const { data: user, isLoading, error, logout } = useAuth();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [publicBaseUrl, setPublicBaseUrl] = useState<string | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  type ApiAsset = {
    id?: string;
    _id?: string;
    object_key: string;
    mime_type?: string;
    mimeType?: string;
    file_size?: number;
    fileSize?: number;
    status?: string;
  };

  type MasteringJob = {
    id?: string;
    _id?: string;
    userId?: string;
    inputAssetId?: string;
    input_asset_id?: string;
    status?: string;
    result_object_key?: string | null;
    preview_object_key?: string | null;
    updated_at?: string;
    created_at?: string;
  };

  const [assetsList, setAssets] = useState<ApiAsset[]>([]);
  const [jobsByAssetId, setJobsByAssetId] = useState<
    Record<string, MasteringJob>
  >({});
  const hiddenFileInputRef = useRef<HTMLInputElement | null>(null);

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
    setStatus("idle");
    setJobId(null);
    setJobStatus(null);
    setErrorText(null);
    setResultUrl(null);
    setPreviewUrl(null);
  }

  async function uploadAndStart(fileOverride?: File | null) {
    try {
      setErrorText(null);
      setResultUrl(null);
      setPreviewUrl(null);
      const file = fileOverride ?? selectedFile;
      if (!file) {
        setStatus("Please select a file first.");
        return;
      }

      setStatus("Creating asset...");
      const assetRes = await fetch("/api/assets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          file_name: file.name,
          file_type: file.type || "audio/wav",
          file_size: file.size,
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
      formData.append("file", file);
      const uploadRes = await fetch(url, { method: "POST", body: formData });
      if (
        !(uploadRes.status === 204 || uploadRes.status === 201 || uploadRes.ok)
      ) {
        const text = await uploadRes.text();
        setStatus(`Upload failed ${uploadRes.status}`);
        setErrorText(text.slice(0, 500));
        return;
      }
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

      // Refresh lists
      await loadAssetsAndJobs();
    } catch (e: unknown) {
      setStatus("Unexpected error");
      setErrorText(e instanceof Error ? e.message : String(e));
    }
  }

  // Manual job status checker removed; live updates via WebSocket

  function getAssetId(a: ApiAsset): string | undefined {
    return a.id ?? a._id;
  }

  function getMimeType(a: ApiAsset): string {
    return a.mime_type ?? a.mimeType ?? "";
  }

  function getExtLabel(a: ApiAsset): string {
    const mime = getMimeType(a).toLowerCase();
    if (mime.includes("wav")) return "WAV";
    if (mime.includes("mpeg")) return "MP3";
    if (mime.includes("flac")) return "FLAC";
    if (mime.includes("aiff")) return "AIFF";
    const key = a.object_key || "";
    const m = key.match(/\.([a-z0-9]+)$/i);
    return m ? m[1].toUpperCase() : "BIN";
  }

  const loadAssetsAndJobs = useCallback(async () => {
    try {
      const [assetsRes, jobsRes] = await Promise.all([
        fetch("/api/assets", { credentials: "include" }),
        fetch("/api/mastering/jobs", { credentials: "include" }),
      ]);
      if (assetsRes.ok) {
        const list = (await assetsRes.json()) as ApiAsset[];
        setAssets(Array.isArray(list) ? list : []);
      }
      if (jobsRes.ok) {
        const jobs = (await jobsRes.json()) as MasteringJob[];
        const map: Record<string, MasteringJob> = {};
        for (const job of jobs) {
          const assetId = job.inputAssetId ?? job.input_asset_id;
          if (!assetId) continue;
          if (!map[assetId]) map[assetId] = job;
        }
        setJobsByAssetId(map);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    // Initial load
    loadAssetsAndJobs();
  }, [loadAssetsAndJobs]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${window.location.host}/api/ws`);
      ws.onmessage = (ev: MessageEvent) => {
        try {
          const data = JSON.parse(ev.data);
          if (data?.type === "job.update" && data?.job) {
            const job = data.job as MasteringJob;
            const assetId = job.inputAssetId ?? job.input_asset_id;
            if (assetId) {
              setJobsByAssetId((prev) => ({ ...prev, [assetId]: job }));
            }
            const jobIdStr = job.id ?? job._id;
            if (jobIdStr && jobIdStr === jobId) {
              const st: string | undefined = job.status;
              setJobStatus(st || null);
              if (st === "done") {
                const base =
                  publicBaseUrl ||
                  (process.env.NEXT_PUBLIC_PUBLIC_BUCKET_URL as
                    | string
                    | undefined) ||
                  "";
                const resultKey: string | undefined =
                  job.result_object_key || undefined;
                const previewKey: string | undefined =
                  job.preview_object_key || undefined;
                if (base && resultKey) setResultUrl(`${base}/${resultKey}`);
                if (base && previewKey) setPreviewUrl(`${base}/${previewKey}`);
              }
            }
          }
        } catch {
          // ignore malformed
        }
      };
      return () => {
        try {
          ws.close();
        } catch {
          // ignore
        }
      };
    } catch {
      // ignore
    }
  }, [jobId, publicBaseUrl]);

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
      <main className="flex flex-col gap-4 items-stretch w-full max-w-2xl mx-auto p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Uploaded assets</h1>
          <div className="flex items-center gap-2">
            <input
              ref={hiddenFileInputRef}
              type="file"
              accept="audio/*"
              className="hidden"
              onChange={(e) => {
                onFileChange(e);
                const f = e.target.files?.[0] || null;
                if (f) void uploadAndStart(f);
              }}
            />
            <button
              className="px-3 py-2 rounded bg-blue-600 text-white"
              onClick={() => hiddenFileInputRef.current?.click()}
            >
              Upload & Master
            </button>
          </div>
        </div>

        <div className="mt-2 flex flex-col gap-2">
          {assetsList.length === 0 ? (
            <div className="text-sm opacity-70">No assets yet.</div>
          ) : (
            <div className="flex flex-col divide-y border rounded">
              {assetsList.map((a, idx) => {
                const id = getAssetId(a) || String(idx);
                const job = jobsByAssetId[id];
                const st = job?.status || a.status || "created";
                const base =
                  publicBaseUrl ||
                  (process.env.NEXT_PUBLIC_PUBLIC_BUCKET_URL as
                    | string
                    | undefined) ||
                  "";
                const filename = a.object_key.split("/").pop() || a.object_key;
                const format = getExtLabel(a);
                const downloadHref = base
                  ? `${base}/${a.object_key}`
                  : undefined;
                return (
                  <div
                    key={id}
                    className="flex items-center justify-between px-4 py-3"
                  >
                    <div className="flex flex-col">
                      <div className="font-medium text-sm break-all">
                        {filename}
                      </div>
                      <div className="text-xs opacity-70">
                        format: {format} • status: {st}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {downloadHref ? (
                        <a
                          className="text-sm px-2 py-1 rounded border hover:bg-zinc-50"
                          href={downloadHref}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Download
                        </a>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
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
