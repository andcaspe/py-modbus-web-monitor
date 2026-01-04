import { ConnectionConfig, MonitorStatus } from "../types";

interface Props {
  status: MonitorStatus;
  connection: ConnectionConfig;
  apiBase: string;
  onApiBaseChange(value: string): void;
  onChange(connection: ConnectionConfig): void;
  onConnect(): void;
  onDisconnect(): void;
}

const statusCopy: Record<MonitorStatus, string> = {
  disconnected: "Offline",
  connecting: "Connecting",
  connected: "Streaming",
};

export default function ConnectionForm({
  status,
  connection,
  apiBase,
  onApiBaseChange,
  onChange,
  onConnect,
  onDisconnect,
}: Props) {
  const canConnect = status === "disconnected";
  return (
    <div className="panel stack">
      <div className="header" style={{ marginBottom: 0 }}>
        <h3>Connection</h3>
        <span className="status">
          <span
            className={`dot ${
              status === "connected" ? "ok" : status === "connecting" ? "busy" : ""
            }`}
          />
          {statusCopy[status]}
        </span>
      </div>
      <div className="field">
        <label>API base URL</label>
        <input
          value={apiBase}
          onChange={(e) => onApiBaseChange(e.target.value)}
          placeholder="http://localhost:8000"
        />
      </div>
      <div className="stack">
        <div className="field">
          <label>Host</label>
          <input
            value={connection.host}
            onChange={(e) => onChange({ ...connection, host: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Port</label>
          <input
            type="number"
            value={connection.port}
            onChange={(e) =>
              onChange({ ...connection, port: Number.parseInt(e.target.value || "502", 10) })
            }
          />
        </div>
        <div className="field">
          <label>Unit ID</label>
          <input
            type="number"
            value={connection.unitId}
            onChange={(e) =>
              onChange({ ...connection, unitId: Number.parseInt(e.target.value || "1", 10) })
            }
          />
        </div>
        <div className="field">
          <label>Poll interval (s)</label>
          <input
            type="number"
            min="0.005"
            step="0.001"
            value={connection.interval}
            onChange={(e) =>
              onChange({
                ...connection,
                interval: Number.parseFloat(e.target.value || "1"),
              })
            }
          />
        </div>
      </div>
      <div className="button-row">
        <button className="primary" onClick={onConnect} disabled={!canConnect}>
          Connect &amp; Monitor
        </button>
        <button className="secondary" onClick={onDisconnect} disabled={status === "disconnected"}>
          Disconnect
        </button>
      </div>
    </div>
  );
}
