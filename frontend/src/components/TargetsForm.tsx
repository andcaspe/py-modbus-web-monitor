import { TargetConfig } from "../types";

interface Props {
  targets: TargetConfig[];
  onChange(targets: TargetConfig[]): void;
}

const kinds = [
  { value: "holding", label: "Holding Register" },
  { value: "input", label: "Input Register" },
  { value: "coil", label: "Coil" },
  { value: "discrete", label: "Discrete Input" },
];

export default function TargetsForm({ targets, onChange }: Props) {
  const update = (idx: number, patch: Partial<TargetConfig>) => {
    const next = targets.slice();
    next[idx] = { ...next[idx], ...patch };
    onChange(next);
  };

  const add = () =>
    onChange([
      ...targets,
      {
        kind: "holding",
        address: Math.max(0, (targets.at(-1)?.address ?? 0) + 1),
        count: 1,
        label: "",
      },
    ]);

  const remove = (idx: number) => onChange(targets.filter((_, i) => i !== idx));

  return (
    <div className="panel stack">
      <div className="header" style={{ marginBottom: 0 }}>
        <h3>Targets to monitor</h3>
        <span className="badge">{targets.length} selected</span>
      </div>
      <div className="targets">
        {targets.map((target, idx) => (
          <div key={`${target.kind}-${idx}`} className="target-row">
            <select
              value={target.kind}
              onChange={(e) => update(idx, { kind: e.target.value as TargetConfig["kind"] })}
            >
              {kinds.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
            <input
              type="number"
              value={target.address}
              onChange={(e) =>
                update(idx, { address: Number.parseInt(e.target.value || "0", 10) })
              }
              placeholder="Address"
            />
            <input
              type="number"
              value={target.count}
              min={1}
              max={125}
              onChange={(e) =>
                update(idx, { count: Number.parseInt(e.target.value || "1", 10) })
              }
              placeholder="Count"
            />
            <input
              value={target.label ?? ""}
              onChange={(e) => update(idx, { label: e.target.value })}
              placeholder="Label"
            />
            <button className="ghost" onClick={() => remove(idx)} title="Remove row">
              ✕
            </button>
          </div>
        ))}
      </div>
      <button className="ghost" onClick={add}>
        + Add target
      </button>
    </div>
  );
}
