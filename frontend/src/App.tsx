import { useEffect, useMemo, useRef, useState } from "react";
import ChartPanel from "./components/ChartPanel";
import ConnectionForm from "./components/ConnectionForm";
import LiveTable from "./components/LiveTable";
import TargetsForm from "./components/TargetsForm";
import WritePanel from "./components/WritePanel";
import {
  ConnectionConfig,
  HistoryPoint,
  LiveValue,
  MonitorStatus,
  TargetConfig,
  WriteOperationInput,
} from "./types";

const defaultApiBase =
  (typeof window !== "undefined" && `${window.location.protocol}//${window.location.hostname}:8000`) ||
  "http://localhost:8000";
const envApiBase = import.meta.env.VITE_API_BASE as string | undefined;

const toWebsocketUrl = (apiBase: string) => {
  try {
    const url = new URL(apiBase);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/ws/monitor";
    url.hash = "";
    url.search = "";
    return url.toString();
  } catch {
    const cleaned = apiBase.replace(/\/+$/, "");
    return `${cleaned.replace(/^http/, "ws")}/ws/monitor`;
  }
};

const keyFor = (target: { kind: string; address: number }) => `${target.kind}:${target.address}`;

export default function App() {
  const [apiBase, setApiBase] = useState(envApiBase || defaultApiBase);
  const [connection, setConnection] = useState<ConnectionConfig>({
    protocol: "tcp",
    host: "127.0.0.1",
    port: 502,
    unitId: 1,
    interval: 1,
  });
  const [targets, setTargets] = useState<TargetConfig[]>([
    { kind: "holding", address: 0, count: 1, label: "Register 0" },
  ]);
  const [status, setStatus] = useState<MonitorStatus>("disconnected");
  const [latest, setLatest] = useState<LiveValue[]>([]);
  const [history, setHistory] = useState<Record<string, HistoryPoint[]>>({});
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const wsUrl = useMemo(() => toWebsocketUrl(apiBase), [apiBase]);

  const pushLog = (entry: string) =>
    setLogs((prev) => [entry, ...prev].slice(0, 80)); // keep recent entries

  useEffect(
    () => () => {
      wsRef.current?.close();
    },
    [],
  );

  const handleMessage = (event: MessageEvent) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === "update") {
        const values = payload.data as LiveValue[];
        setLatest(values);
        const timestamp = payload.timestamp ? Date.parse(payload.timestamp) : Date.now();
        setHistory((prev) => {
          const next = { ...prev };
          values.forEach((value) => {
            const key = keyFor(value);
            const numeric = Number(value.values[0] ?? 0);
            const coerced = Number.isNaN(numeric) ? (value.values[0] ? 1 : 0) : numeric;
            const points = [...(next[key] ?? []), { timestamp, value: coerced }];
            next[key] = points.slice(-200);
          });
          return next;
        });
      } else if (payload.type === "status" || payload.type === "ack") {
        pushLog(payload.message || JSON.stringify(payload));
      } else if (payload.type === "error") {
        pushLog(`Error: ${payload.message}`);
      }
    } catch (err) {
      pushLog(`Invalid message: ${err}`);
    }
  };

  const connect = () => {
    wsRef.current?.close();
    setStatus("connecting");
    pushLog(`Connecting to ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      pushLog(
        `Connected. Subscribing to monitor stream at ${connection.host}:${connection.port} (unit ${connection.unitId})...`,
      );
      const { interval, ...connectionBody } = connection;
      ws.send(
        JSON.stringify({
          type: "configure",
          connection: connectionBody,
          interval,
          targets,
        }),
      );
    };

    ws.onmessage = handleMessage;
    ws.onerror = (e) => pushLog(`Websocket error: ${JSON.stringify(e)}`);
    ws.onclose = () => {
      setStatus("disconnected");
      pushLog("Connection closed");
      wsRef.current = null;
    };
  };

  const disconnect = () => {
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
  };

  const parseWriteValue = (value: string, kind: "holding" | "coil") => {
    const parts = value
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean);
    if (parts.length === 0) {
      throw new Error("Value required");
    }
    if (kind === "coil") {
      const asBools = parts.map((p) => ["1", "true", "on", "yes"].includes(p.toLowerCase()));
      return asBools.length === 1 ? asBools[0] : asBools;
    }
    const nums = parts.map((p) => Number.parseInt(p, 10));
    if (nums.some(Number.isNaN)) {
      throw new Error("Register values must be numbers");
    }
    return nums.length === 1 ? nums[0] : nums;
  };

  const sendWrite = (write: WriteOperationInput) => {
    if (!wsRef.current || status !== "connected") {
      pushLog("Connect before sending writes.");
      return;
    }
    try {
      const value = parseWriteValue(write.value, write.kind);
      wsRef.current.send(JSON.stringify({ type: "write", writes: [{ ...write, value }] }));
      pushLog(`Write sent to ${write.address}`);
    } catch (err) {
      pushLog((err as Error).message);
    }
  };

  const labelMap = useMemo(
    () =>
      Object.fromEntries(
        latest.map((v) => [keyFor(v), v.label || `${v.kind}:${v.address}`]),
      ),
    [latest],
  );

  return (
    <div className="app-shell">
      <div className="header">
        <h1 className="title">Modbus Web Monitor</h1>
        <span className="badge">FastAPI + WebSocket + React</span>
      </div>

      <div className="grid">
        <div className="stack">
          <ConnectionForm
            status={status}
            connection={connection}
            apiBase={apiBase}
            onApiBaseChange={setApiBase}
            onChange={setConnection}
            onConnect={connect}
            onDisconnect={disconnect}
          />
          <TargetsForm targets={targets} onChange={setTargets} />
          <WritePanel disabled={status !== "connected"} onSend={sendWrite} />
          <div className="panel">
            <h3>Logs</h3>
            <div className="logs">{logs.join("\n") || "Waiting for events..."}</div>
          </div>
        </div>
        <div className="stack">
          <LiveTable rows={latest} />
          <ChartPanel history={history} labels={labelMap} />
        </div>
      </div>
    </div>
  );
}
