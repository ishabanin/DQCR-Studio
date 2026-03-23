import { useMemo } from "react";

import type { ValidationRuleResult } from "../../api/projects";
import { useValidationStore } from "../../app/store/validationStore";

export type ValidationBadgeLevel = "error" | "warning" | "info";

interface BadgeAggregate {
  counts: Record<ValidationBadgeLevel, number>;
  messages: string[];
}

export interface ValidationBadgeItem {
  level: ValidationBadgeLevel;
  tooltip: string;
}

function normalizeLevel(status: ValidationRuleResult["status"]): ValidationBadgeLevel | null {
  if (status === "error") return "error";
  if (status === "warning") return "warning";
  if (status === "pass") return "info";
  return null;
}

function levelPriority(level: ValidationBadgeLevel): number {
  if (level === "error") return 3;
  if (level === "warning") return 2;
  return 1;
}

function getAncestorPaths(path: string): string[] {
  const normalized = path.replace(/^\.+\/?/, "").replace(/^\/+|\/+$/g, "");
  if (!normalized) return [];
  const parts = normalized.split("/").filter(Boolean);
  return parts.slice(0, -1).map((_, index) => parts.slice(0, index + 1).join("/"));
}

function appendAggregate(target: Map<string, BadgeAggregate>, path: string, level: ValidationBadgeLevel, message: string): void {
  const existing = target.get(path) ?? {
    counts: { error: 0, warning: 0, info: 0 },
    messages: [],
  };
  existing.counts[level] += 1;
  if (message && existing.messages.length < 3) {
    existing.messages.push(message);
  }
  target.set(path, existing);
}

function buildTooltip(aggregate: BadgeAggregate): string {
  const total = aggregate.counts.error + aggregate.counts.warning + aggregate.counts.info;
  if (total <= 1 && aggregate.messages[0]) return aggregate.messages[0];
  if (aggregate.counts.error > 0) return `${aggregate.counts.error} ошибок`;
  if (aggregate.counts.warning > 0) return `${aggregate.counts.warning} предупреждений`;
  return `${aggregate.counts.info} уведомлений`;
}

export function buildValidationBadges(rules: ValidationRuleResult[]): Map<string, ValidationBadgeItem> {
  const aggregateMap = new Map<string, BadgeAggregate>();

  for (const rule of rules) {
    if (!rule.file_path) continue;
    const level = normalizeLevel(rule.status);
    if (!level) continue;
    const message = typeof rule.message === "string" ? rule.message : "";
    appendAggregate(aggregateMap, rule.file_path, level, message);
    for (const ancestor of getAncestorPaths(rule.file_path)) {
      appendAggregate(aggregateMap, ancestor, level, message);
    }
  }

  const result = new Map<string, ValidationBadgeItem>();
  for (const [path, aggregate] of aggregateMap.entries()) {
    const levels: ValidationBadgeLevel[] = ["info", "warning", "error"];
    const level =
      levels
        .filter((item) => aggregate.counts[item] > 0)
        .sort((a, b) => levelPriority(b) - levelPriority(a))[0] ?? "info";
    result.set(path, { level, tooltip: buildTooltip(aggregate) });
  }
  return result;
}

export function useValidationBadges(projectId: string | null): Map<string, ValidationBadgeItem> {
  const latestRun = useValidationStore((state) => state.latestRun);
  return useMemo(() => {
    if (!projectId || !latestRun) return new Map<string, ValidationBadgeItem>();
    if (latestRun.project !== projectId) return new Map<string, ValidationBadgeItem>();
    return buildValidationBadges(latestRun.rules ?? []);
  }, [latestRun, projectId]);
}
