export type RegisterKind = "holding" | "input" | "coil" | "discrete";

export type MonitorStatus = "disconnected" | "connecting" | "connected";

export interface ConnectionConfig {
  protocol: "tcp";
  host: string;
  port: number;
  unitId: number;
  interval: number;
}

export interface TargetConfig {
  kind: RegisterKind;
  address: number;
  count: number;
  label?: string;
}

export interface LiveValue {
  address: number;
  kind: RegisterKind;
  label: string;
  values: Array<number | boolean>;
}

export interface HistoryPoint {
  timestamp: number;
  value: number;
}

export interface WriteOperationInput {
  kind: "holding" | "coil";
  address: number;
  value: string;
}
