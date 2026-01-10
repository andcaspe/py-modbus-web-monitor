import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import LiveTable from "../src/components/LiveTable";
import type { AnomalySummary, LiveValue } from "../src/types";

const baseRow: LiveValue = {
  address: 1,
  kind: "holding",
  label: "Pump 1",
  values: [42],
};

const buildSummary = (zScore: number | null, sampleCount: number): AnomalySummary => ({
  value: 42,
  zScore,
  sampleCount,
  mean: 40,
  stdev: 2,
  timestamp: 0,
});

describe("LiveTable", () => {
  it("shows disabled anomaly state", () => {
    render(
      <LiveTable rows={[baseRow]} anomalies={{}} threshold={3} minSamples={10} enabled={false} />
    );

    expect(screen.getByText("off")).toBeTruthy();
  });

  it("shows sample count when not enough samples", () => {
    const anomalies = {
      "holding:1": buildSummary(1.2, 3),
    };

    render(
      <LiveTable rows={[baseRow]} anomalies={anomalies} threshold={3} minSamples={10} enabled />
    );

    expect(screen.getByText("n 3/10")).toBeTruthy();
  });

  it("flags alerts when z-score exceeds threshold", () => {
    const anomalies = {
      "holding:1": buildSummary(4.2, 15),
    };

    render(
      <LiveTable rows={[baseRow]} anomalies={anomalies} threshold={3} minSamples={10} enabled />
    );

    const chip = screen.getByText("z 4.20");
    expect(chip.className).toContain("alert");
  });
});
