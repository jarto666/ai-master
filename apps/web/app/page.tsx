"use client";

import { createClient } from "@supabase/supabase-js";
import { useEffect, useMemo, useState } from "react";

export default function Home() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL as string;
  const supabasePublishableKey = process.env
    .NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY as string;
  const supabase = useMemo(
    () => createClient(supabaseUrl, supabasePublishableKey),
    [supabaseUrl, supabasePublishableKey]
  );

  const [status, setStatus] = useState<string>("idle");
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [fileKey, setFileKey] = useState<string>("");
  const [fileType, setFileType] = useState<string>("audio/wav");
  const [fileSize, setFileSize] = useState<number>(1234);
  const [uploadType, setUploadType] = useState<string>("test");

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setUserEmail(data.user?.email ?? null);
    });
  }, [supabase]);

  async function signInWithGoogle() {
    setStatus("redirecting to Google...");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
    });
    if (error) setStatus(`error: ${error.message}`);
    else setStatus("redirected");
  }

  async function syncSessionToApi() {
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData.session?.access_token;
    if (!token) {
      setStatus("no token");
      return;
    }
    const resp = await fetch("/api/auth/session", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      credentials: "include",
    });
    setStatus(`session: ${resp.status}`);
  }

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

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    await supabase.auth.signOut();
    setUserEmail(null);
    setStatus("logged out");
  }

  return (
    <div className="grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <main className="flex flex-col gap-4 row-start-2 items-stretch w-full max-w-xl">
        <h1 className="text-2xl font-semibold">Auth + Presign test</h1>
        <div className="text-sm opacity-80">
          user: {userEmail ?? "anonymous"}
        </div>
        <div className="flex gap-2">
          <button
            className="px-3 py-2 rounded bg-black text-white"
            onClick={signInWithGoogle}
          >
            Sign in with Google (Supabase)
          </button>
          <button
            className="px-3 py-2 rounded bg-zinc-800 text-white"
            onClick={syncSessionToApi}
          >
            Send session to API
          </button>
          <button
            className="px-3 py-2 rounded bg-zinc-700 text-white"
            onClick={logout}
          >
            Logout
          </button>
        </div>
        <div className="mt-4 grid gap-2">
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
      </main>
    </div>
  );
}
