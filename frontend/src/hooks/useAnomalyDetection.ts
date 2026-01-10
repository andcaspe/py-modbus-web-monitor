import { useEffect, useRef, useState } from "react";
import {
  AnomalyPoint,
  AnomalySeries,
  AnomalySummary,
  ConnectionConfig,
  HistoryPoint,
  LiveValue,
  TargetConfig,
} from "../types";

interface Params {
  apiBase: string;
  connection: ConnectionConfig;
  targets: TargetConfig[];
  latest: LiveValue[];
  history: Record<string, HistoryPoint[]>;
  method: "none" | "zscore" | "stl";
  window: number;
  minSamples: number;
  threshold: number;
  active: boolean;
  onError?: (message: string) => void;
}

const keyFor = (target: { kind: string; address: number }) => `${target.kind}:${target.address}`;

export default function useAnomalyDetection({
  apiBase,
  connection,
  targets,
  latest,
  history,
  method,
  window,
  minSamples,
  threshold,
  active,
  onError,
}: Params) {
  const [summary, setSummary] = useState<Record<string, AnomalySummary>>({});
  const [anomalyHistory, setAnomalyHistory] = useState<Record<string, AnomalyPoint[]>>({});
  const historyRef = useRef<Record<string, HistoryPoint[]>>(history);
  const lastFetchRef = useRef<number>(0);
  const requestIdRef = useRef<number>(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    historyRef.current = history;
  }, [history]);

  useEffect(() => {
    if (active && method !== "none") {
      return;
    }
    abortRef.current?.abort();
    requestIdRef.current += 1;
    setSummary({});
    setAnomalyHistory({});
  }, [active, method]);

  useEffect(() => {
    if (!active) {
      return;
    }
    if (method === "none") {
      return;
    }
    if (latest.length === 0) {
      return;
    }
    if (targets.length === 0) {
      return;
    }
    const now = Date.now();
    const minInterval = Math.max(1000, connection.interval * 1000);
    if (now - lastFetchRef.current < minInterval) {
      return;
    }
    lastFetchRef.current = now;
    const requestId = (requestIdRef.current += 1);
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const { interval: _interval, ...connectionBody } = connection;
    const endpoint = method === "stl" ? "stl" : "zscore";
    const safeWindow = Math.max(3, window);
    const safeMinSamples = Math.max(3, Math.min(minSamples, safeWindow));
    fetch(`${apiBase}/api/anomaly/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        connection: connectionBody,
        targets,
        window: safeWindow,
        min_samples: safeMinSamples,
      }),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Anomaly request failed (${response.status})`);
        }
        const payload = (await response.json()) as { data: AnomalySeries[] };
        if (requestId !== requestIdRef.current) {
          return;
        }
        const nextSummary: Record<string, AnomalySummary> = {};
        const timestamp = Date.now();
        payload.data.forEach((series) => {
          const key = keyFor(series);
          nextSummary[key] = {
            value: series.values?.[0] ?? null,
            zScore: series.z_scores?.[0] ?? null,
            sampleCount: series.sample_counts?.[0] ?? 0,
            mean: series.mean?.[0] ?? null,
            stdev: series.stdev?.[0] ?? null,
            timestamp,
          };
        });
        setSummary(nextSummary);
        setAnomalyHistory((prev) => {
          const next: Record<string, AnomalyPoint[]> = { ...prev };
          Object.entries(nextSummary).forEach(([key, entry]) => {
            if (entry.zScore === null || entry.value === null) {
              return;
            }
            if (Math.abs(entry.zScore) < threshold) {
              return;
            }
            const historyPoints = historyRef.current[key] ?? [];
            const lastTimestamp =
              historyPoints.length > 0
                ? historyPoints[historyPoints.length - 1].timestamp
                : entry.timestamp;
            const point: AnomalyPoint = {
              timestamp: lastTimestamp,
              value: entry.value,
              zScore: entry.zScore,
            };
            const updated = [...(next[key] ?? []), point];
            next[key] = updated.slice(-200);
          });
          return next;
        });
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        onError?.(`Anomaly fetch error: ${err}`);
      });
  }, [
    active,
    apiBase,
    connection,
    latest,
    method,
    minSamples,
    onError,
    targets,
    threshold,
    window,
  ]);

  return { summary, history: anomalyHistory };
}
