import { apiFetch } from "./client";
import type { PipelineRunResponse } from "../types/api";

export const runPipeline = (
  token: string,
  max_results: number = 10,
  after_days: number | null = null,
): Promise<PipelineRunResponse> =>
  apiFetch<PipelineRunResponse>("/api/v1/pipeline/run", {
    method: "POST",
    body: JSON.stringify({ max_results, after_days }),
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
