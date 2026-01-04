import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnomalyPoint, HistoryPoint } from "../types";

interface Props {
  history: Record<string, HistoryPoint[]>;
  labels: Record<string, string>;
  anomalies: Record<string, AnomalyPoint[]>;
}

const palette = ["#5de4c7", "#7aa2f7", "#f59e0b", "#f43f5e", "#34d399", "#c084fc"];

export default function ChartPanel({ history, labels, anomalies }: Props) {
  const keys = Object.keys(history);
  const merged: Record<number, Record<string, number | undefined>> = {};

  keys.forEach((key) => {
    history[key]?.forEach((point) => {
      merged[point.timestamp] ??= { timestamp: point.timestamp };
      merged[point.timestamp][key] = point.value;
    });
  });

  Object.entries(anomalies).forEach(([key, points]) => {
    points.forEach((point) => {
      merged[point.timestamp] ??= { timestamp: point.timestamp };
      merged[point.timestamp][`${key}__anomaly`] = point.value;
    });
  });

  const data = Object.values(merged).sort(
    (a, b) => (a.timestamp as number) - (b.timestamp as number),
  );

  if (keys.length === 0 || data.length === 0) {
    return (
      <div className="panel chart-panel">
        <h3>Trends</h3>
        <p style={{ color: "var(--muted)" }}>No samples yet. Start monitoring to see plots.</p>
      </div>
    );
  }

  const renderAnomalyDot =
    (key: string) =>
    (props: { cx?: number; cy?: number; payload?: Record<string, number | undefined> }) => {
      const { cx, cy, payload } = props;
      if (!payload) return null;
      if (payload[`${key}__anomaly`] === undefined) return null;
      if (cx === undefined || cy === undefined) return null;
      return (
        <circle
          cx={cx}
          cy={cy}
          r={5}
          fill="var(--danger)"
          stroke="rgba(15, 23, 42, 0.9)"
          strokeWidth={1.5}
        />
      );
    };

  return (
    <div className="panel chart-panel">
      <div className="header" style={{ marginBottom: 8 }}>
        <h3>Trends</h3>
        <span className="chip">Last {data.length} samples</span>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(value) => new Date(value).toLocaleTimeString()}
            stroke="var(--muted)"
          />
          <YAxis stroke="var(--muted)" />
          <Tooltip
            labelFormatter={(value) => new Date(value).toLocaleTimeString()}
            contentStyle={{ background: "#0c1221", border: "1px solid rgba(255,255,255,0.1)" }}
          />
          <Legend />
          {keys.map((key, idx) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={labels[key] || key}
              stroke={palette[idx % palette.length]}
              strokeWidth={2}
              dot={renderAnomalyDot(key)}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
