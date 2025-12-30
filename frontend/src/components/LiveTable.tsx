import { LiveValue } from "../types";

interface Props {
  rows: LiveValue[];
}

export default function LiveTable({ rows }: Props) {
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
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.kind}-${row.address}`}>
              <td>{row.label}</td>
              <td>
                <span className="pill">{row.kind}</span>
              </td>
              <td>{row.address}</td>
              <td>{row.values.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p style={{ color: "var(--muted)" }}>Connect to a device to see values.</p>
      )}
    </div>
  );
}
