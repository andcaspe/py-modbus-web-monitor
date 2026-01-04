interface Props {
  method: "none" | "zscore" | "stl";
  window: number;
  minSamples: number;
  threshold: number;
  onMethodChange(value: "none" | "zscore" | "stl"): void;
  onWindowChange(value: number): void;
  onMinSamplesChange(value: number): void;
  onThresholdChange(value: number): void;
}

export default function AnomalyControls({
  method,
  window,
  minSamples,
  threshold,
  onMethodChange,
  onWindowChange,
  onMinSamplesChange,
  onThresholdChange,
}: Props) {
  const isEnabled = method !== "none";
  return (
    <div className="panel">
      <div className="header" style={{ marginBottom: 10 }}>
        <h3>Anomaly settings</h3>
        <span className="chip">{method === "none" ? "off" : method}</span>
      </div>
      <div className="inline-fields">
        <div className="field inline">
          <label>Algorithm</label>
          <select
            value={method}
            onChange={(e) => onMethodChange(e.target.value as "none" | "zscore" | "stl")}
          >
            <option value="none">Off</option>
            <option value="zscore">Z-score</option>
            <option value="stl">STL residual</option>
          </select>
        </div>
        <div className="field inline">
          <label>Window (samples)</label>
          <input
            type="number"
            min={3}
            step={1}
            value={window}
            onChange={(e) => onWindowChange(Number.parseInt(e.target.value || "3", 10))}
            disabled={!isEnabled}
          />
        </div>
        <div className="field inline">
          <label>Min samples</label>
          <input
            type="number"
            min={3}
            step={1}
            value={minSamples}
            onChange={(e) => onMinSamplesChange(Number.parseInt(e.target.value || "3", 10))}
            disabled={!isEnabled}
          />
        </div>
        <div className="field inline">
          <label>Threshold (|z|)</label>
          <input
            type="number"
            min={0}
            step={0.1}
            value={threshold}
            onChange={(e) => onThresholdChange(Number.parseFloat(e.target.value || "0"))}
            disabled={!isEnabled}
          />
        </div>
      </div>
    </div>
  );
}
