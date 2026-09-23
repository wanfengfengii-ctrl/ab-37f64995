import type { AdjudicateResponse, Event, Params } from "./types";

export function apiBase(): string {
  return (window.__ENV__ && window.__ENV__.apiBase) || "";
}

export class ApiError extends Error {
  details: unknown;

  constructor(message: string, details?: unknown) {
    super(message);
    this.details = details;
  }
}

export async function adjudicate(
  streamA: Event[],
  streamB: Event[],
  params: Params,
): Promise<AdjudicateResponse> {
  let res: Response;
  try {
    res = await fetch(`${apiBase()}/api/adjudicate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        streamA,
        streamB,
        minOffset: params.minOffset,
        maxOffset: params.maxOffset,
        jump: params.jump,
        minHits: params.minHits,
      }),
    });
  } catch (e) {
    throw new ApiError(`无法连接裁决 API：${(e as Error).message}`);
  }

  if (!res.ok) {
    let details: unknown = null;
    try {
      details = await res.json();
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(`API 返回 ${res.status}`, details);
  }
  return (await res.json()) as AdjudicateResponse;
}
