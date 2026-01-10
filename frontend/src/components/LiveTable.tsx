import { AnomalySummary, LiveValue } from "../types";

interface Props {
  rows: LiveValue[];
  anomalies: Record<string, AnomalySummary | undefined>;
  threshold: number;
  minSamples: number;
  enabled: boolean;
}

export default function LiveTable({ rows, anomalies, threshold, minSamples, enabled }: Props) {
  return (
    <div className="panel">
      <div className="header" style={{ marginBottom: 10 }}>
        <h3>Live values</h3>
        <span className="chip">{rows.length} signals</span>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Label</th>
            <th>Kind</th>
            <th>Address</th>
            <th>Values</th>
            <th>Anomaly</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const key = `${row.kind}:${row.address}`;
            const summary = anomalies[key];
            const zScore = summary?.zScore ?? null;
            const sampleCount = summary?.sampleCount ?? 0;
            const isReady = enabled && sampleCount >= minSamples && zScore !== null;
            const isAlert = isReady && Math.abs(zScore) >= threshold;
            const label = enabled
              ? isReady
                ? `z ${zScore.toFixed(2)}`
                : `n ${sampleCount}/${minSamples}`
              : "off";
            return (
              <tr key={`${row.kind}-${row.address}`}>
                <td>{row.label}</td>
                <td>
                  <span className="pill">{row.kind}</span>
                </td>
                <td>{row.address}</td>
                <td>{row.values.join(", ")}</td>
                <td>
                  <span
                    className={`chip anomaly-chip ${isAlert ? "alert" : isReady ? "ok" : "muted"}`}
                  >
                    {label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p style={{ color: "var(--muted)" }}>Connect to a device to see values.</p>
      )}
    </div>
  );
}
