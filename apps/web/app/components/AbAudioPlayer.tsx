import React, { useEffect, useRef, useState, useCallback } from "react";

/**
 * React AB Audio Player — two tracks kept in lockstep with A/B switching and optional crossfade.
 *
 * Features
 * - Precise sync using Web Audio API (single AudioContext)
 * - Play/Pause, Seek, A/B switch, optional Crossfade, Master Volume
 * - Works with different sample rates (decoded buffers are resampled by the browser)
 * - Minimal UI (Tailwind classes). Replace as you like.
 *
 * Notes
 * - Because AudioBufferSourceNode is one-shot, we recreate sources on seek and on (re)play.
 * - We schedule both sources to start at the same time with the same offset.
 * - For long tracks you may want drift correction; for typical music-length tracks this is sufficient.
 */

export type ABPlayerProps = {
  urlA: string;
  urlB?: string;
  labelA?: string;
  labelB?: string;
  /** ms for crossfade when switching A/B */
  crossfadeMs?: number;
  /** initial audible side */
  initialSide?: "A" | "B";
  /** start playing immediately after load */
  autoloadPlay?: boolean;
  /** overall volume 0..1 */
  volume?: number;
  /** called when load or decode fails */
  onError?: (e: unknown) => void;
  /** className for outer wrapper */
  className?: string;
};

// Utilities
const clamp = (v: number, min: number, max: number) =>
  Math.min(max, Math.max(min, v));

export default function ABAudioPlayer({
  urlA,
  urlB,
  labelA = "A",
  labelB = "B",
  crossfadeMs = 120,
  initialSide = "A",
  autoloadPlay = false,
  volume = 1,
  onError,
  className,
}: ABPlayerProps) {
  // Audio graph refs
  const audioCtxRef = useRef<AudioContext | null>(null);
  const masterGainRef = useRef<GainNode | null>(null);
  const gainARef = useRef<GainNode | null>(null);
  const gainBRef = useRef<GainNode | null>(null);
  const srcARef = useRef<AudioBufferSourceNode | null>(null);
  const srcBRef = useRef<AudioBufferSourceNode | null>(null);

  // Buffers
  const bufARef = useRef<AudioBuffer | null>(null);
  const bufBRef = useRef<AudioBuffer | null>(null);

  // Playback clock state
  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeSide, setActiveSide] = useState<"A" | "B">(initialSide);
  const [duration, setDuration] = useState<number>(0);
  // `offset` is the logical playback position in seconds (accumulates when paused)
  const offsetRef = useRef<number>(0);
  // `startedAt` is AudioContext time when current play started
  const startedAtRef = useRef<number | null>(null);
  // requestAnimationFrame for time updates
  const rafRef = useRef<number | null>(null);
  const [uiTime, setUiTime] = useState(0);

  // Init audio context lazily
  const getCtx = useCallback(() => {
    if (!audioCtxRef.current) {
      const ctx = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext)();
      // Build graph: master -> destination; two branch gains -> master
      const master = ctx.createGain();
      master.gain.value = clamp(volume, 0, 1);
      master.connect(ctx.destination);
      const gA = ctx.createGain();
      const gB = ctx.createGain();
      gA.connect(master);
      gB.connect(master);
      audioCtxRef.current = ctx;
      masterGainRef.current = master;
      gainARef.current = gA;
      gainBRef.current = gB;
    }
    return audioCtxRef.current!;
  }, [volume]);

  // Volume external control
  useEffect(() => {
    if (masterGainRef.current) {
      masterGainRef.current.gain.setTargetAtTime(
        clamp(volume, 0, 1),
        getCtx().currentTime,
        0.01
      );
    }
  }, [volume, getCtx]);

  // Load & decode
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const ctx = getCtx();
        const fetches = [fetch(urlA).then((r) => r.arrayBuffer())];
        if (urlB) {
          fetches.push(fetch(urlB).then((r) => r.arrayBuffer()));
        }
        const [arrA, arrB] = await Promise.all(fetches);

        const decodes = [ctx.decodeAudioData(arrA.slice(0))];
        if (urlB && arrB) {
          decodes.push(ctx.decodeAudioData(arrB.slice(0)));
        }
        const [bufA, bufB] = await Promise.all(decodes);

        if (cancelled) return;
        bufARef.current = bufA;
        if (bufB) {
          bufBRef.current = bufB;
        }
        const dur = bufB
          ? Math.max(bufA.duration, bufB.duration)
          : bufA.duration;
        setDuration(dur);
        setIsReady(true);
        // set initial audible side
        if (gainARef.current && gainBRef.current) {
          const onA = initialSide === "A" ? 1 : 0;
          const onB = initialSide === "B" ? 1 : 0;
          gainARef.current.gain.value = onA;
          gainBRef.current.gain.value = onB;
        }
        if (autoloadPlay) {
          play();
        }
      } catch (e) {
        console.error(e);
        onError?.(e);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlA, urlB]);

  // Create new one-shot sources wired to branch gains
  const wireSources = (ctx: AudioContext) => {
    const srcA = ctx.createBufferSource();
    srcA.buffer = bufARef.current;
    srcA.connect(gainARef.current!);
    srcA.onended = () => {
      // If both ended (we start them together), finalize when A ends at or after duration
      if (isPlaying) {
        stopInternal(false /*keepOffset*/);
        // snap offset to duration
        offsetRef.current = duration;
        setUiTime(duration);
      }
    };
    srcARef.current = srcA;

    if (bufBRef.current) {
      const srcB = ctx.createBufferSource();
      srcB.buffer = bufBRef.current;
      srcB.connect(gainBRef.current!);
      srcBRef.current = srcB;
    }
  };

  const clearSources = () => {
    try {
      srcARef.current?.disconnect();
    } catch {}
    srcARef.current = null;
    if (srcBRef.current) {
      try {
        srcBRef.current.disconnect();
      } catch {}
      srcBRef.current = null;
    }
  };

  const startRaf = () => {
    const tick = () => {
      const ctx = getCtx();
      let t = offsetRef.current;
      if (isPlaying && startedAtRef.current != null) {
        t = ctx.currentTime - startedAtRef.current + offsetRef.current;
      }
      setUiTime(Math.min(duration, Math.max(0, t)));
      rafRef.current = requestAnimationFrame(tick);
    };
    if (rafRef.current == null) rafRef.current = requestAnimationFrame(tick);
  };

  const stopRaf = () => {
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  };

  const play = () => {
    if (!isReady || isPlaying) return;
    const ctx = getCtx();
    if (ctx.state === "suspended") ctx.resume();

    clearSources();
    wireSources(ctx);

    const when = ctx.currentTime + 0.06; // small scheduling lead
    const startOffset = clamp(offsetRef.current, 0, duration - 1e-6);
    srcARef.current!.start(
      when,
      Math.min(startOffset, bufARef.current?.duration ?? startOffset)
    );
    if (srcBRef.current) {
      srcBRef.current.start(
        when,
        Math.min(startOffset, bufBRef.current?.duration ?? startOffset)
      );
    }

    startedAtRef.current = when;
    setIsPlaying(true);
    startRaf();
  };

  const pause = () => {
    if (!isPlaying) return;
    const ctx = getCtx();
    // compute new offset up to now
    if (startedAtRef.current != null) {
      const elapsed = ctx.currentTime - startedAtRef.current;
      offsetRef.current = clamp(offsetRef.current + elapsed, 0, duration);
    }
    stopInternal(true /* keepOffset */);
  };

  const stopInternal = (keepOffset: boolean) => {
    try {
      srcARef.current?.stop();
    } catch {}
    try {
      srcBRef.current?.stop();
    } catch {}
    clearSources();
    setIsPlaying(false);
    startedAtRef.current = null;
    if (!keepOffset) offsetRef.current = 0;
    stopRaf();
  };

  const stop = () => stopInternal(false);

  const switchSide = (side: "A" | "B") => {
    if (activeSide === side) return;
    setActiveSide(side);
    const ctx = getCtx();
    const t = ctx.currentTime;
    const timeConstant = Math.max(0.001, (crossfadeMs / 1000) * 0.2);
    // Simple equal-power-ish crossfade via exponential approach
    if (gainARef.current && gainBRef.current) {
      if (side === "A") {
        gainARef.current.gain.setTargetAtTime(1, t, timeConstant);
        gainBRef.current.gain.setTargetAtTime(0, t, timeConstant);
      } else {
        gainARef.current.gain.setTargetAtTime(0, t, timeConstant);
        gainBRef.current.gain.setTargetAtTime(1, t, timeConstant);
      }
    }
  };

  const seek = (nextSeconds: number) => {
    const next = clamp(nextSeconds, 0, duration);
    offsetRef.current = next;
    if (isPlaying) {
      // Restart from new offset
      const ctx = getCtx();
      try {
        srcARef.current?.stop();
      } catch {}
      try {
        srcBRef.current?.stop();
      } catch {}
      clearSources();
      wireSources(ctx);
      const when = ctx.currentTime + 0.05;
      srcARef.current!.start(
        when,
        Math.min(next, bufARef.current?.duration ?? next)
      );
      if (srcBRef.current) {
        srcBRef.current.start(
          when,
          Math.min(next, bufBRef.current?.duration ?? next)
        );
      }
      startedAtRef.current = when;
    } else {
      setUiTime(next);
    }
  };

  // Cleanup on unmount
  useEffect(
    () => () => {
      try {
        srcARef.current?.stop();
      } catch {}
      try {
        srcBRef.current?.stop();
      } catch {}
      clearSources();
      stopRaf();
      try {
        audioCtxRef.current?.close();
      } catch {}
    },
    []
  );

  // UI helpers
  const fmt = (s: number) => {
    if (!isFinite(s)) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div
      className={
        "w-full max-w-xl rounded-2xl bg-white/70 p-4 shadow " +
        (className ?? "")
      }
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-medium text-gray-600">AB Audio Player</div>
        <div className="text-xs text-gray-500">
          {isReady ? "ready" : "loading…"}
        </div>
      </div>

      {/* Transport */}
      <div className="flex items-center gap-2">
        {!isPlaying ? (
          <button
            onClick={play}
            disabled={!isReady}
            className="rounded-xl bg-black px-3 py-2 text-white disabled:opacity-50"
          >
            ▶ Play
          </button>
        ) : (
          <button
            onClick={pause}
            className="rounded-xl bg-black px-3 py-2 text-white"
          >
            ❚❚ Pause
          </button>
        )}
        <button
          onClick={stop}
          className="rounded-xl border border-gray-300 px-3 py-2"
        >
          ■ Stop
        </button>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-gray-600">Vol</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={clamp(volume, 0, 1)}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              masterGainRef.current?.gain.setTargetAtTime(
                clamp(v, 0, 1),
                getCtx().currentTime,
                0.01
              );
            }}
          />
        </div>
      </div>

      {/* Timeline */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>{fmt(uiTime)}</span>
          <span>{fmt(duration)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={duration || 0}
          step={0.01}
          value={uiTime}
          onChange={(e) => seek(parseFloat(e.target.value))}
          className="w-full"
        />
      </div>

      {/* A/B switch */}
      {urlB && (
        <div className="mt-4 flex items-center gap-2">
          <span className="text-xs text-gray-600">Active:</span>
          <button
            onClick={() => switchSide("A")}
            className={`rounded-xl px-3 py-2 ${
              activeSide === "A"
                ? "bg-blue-600 text-white"
                : "border border-gray-300"
            }`}
          >
            {labelA}
          </button>
          <button
            onClick={() => switchSide("B")}
            className={`rounded-xl px-3 py-2 ${
              activeSide === "B"
                ? "bg-blue-600 text-white"
                : "border border-gray-300"
            }`}
          >
            {labelB}
          </button>
          <div className="ml-auto text-xs text-gray-600">
            Crossfade: {crossfadeMs}ms
          </div>
        </div>
      )}

      {/* Tips */}
      {urlB && (
        <div className="mt-3 text-xs text-gray-500">
          <p>
            Both tracks are always playing in sync; the A/B buttons change which
            branch is audible via gain.
          </p>
        </div>
      )}
    </div>
  );
}
