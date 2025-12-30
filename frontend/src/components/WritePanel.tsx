import { useState } from "react";
import { WriteOperationInput } from "../types";

interface Props {
  disabled?: boolean;
  onSend(write: WriteOperationInput): void;
}

export default function WritePanel({ disabled, onSend }: Props) {
  const [form, setForm] = useState<WriteOperationInput>({
    kind: "holding",
    address: 0,
    value: "0",
  });

  const send = () => onSend(form);

  return (
    <div className="panel stack">
      <div className="header" style={{ marginBottom: 0 }}>
        <h3>Write</h3>
        <span className="chip">Single/multi supported</span>
      </div>
      <div className="target-row">
        <select
          value={form.kind}
          onChange={(e) => setForm({ ...form, kind: e.target.value as WriteOperationInput["kind"] })}
        >
          <option value="holding">Holding register</option>
          <option value="coil">Coil</option>
        </select>
        <input
          type="number"
          value={form.address}
          onChange={(e) =>
            setForm({ ...form, address: Number.parseInt(e.target.value || "0", 10) })
          }
          placeholder="Address"
        />
        <input
          value={form.value}
          onChange={(e) => setForm({ ...form, value: e.target.value })}
          placeholder="Value (e.g. 1 or 10,11)"
        />
        <button className="primary" onClick={send} disabled={disabled}>
          Send
        </button>
      </div>
      <p style={{ color: "var(--muted)", margin: 0, fontSize: 13 }}>
        For coils, values convert to booleans (1/0/true/false). Comma-separate to write multiple
        registers/coils starting at the address.
      </p>
    </div>
  );
}
