export interface Event {
  time: number;
  code: string;
}

export type JumpDirection = "none" | "plus" | "minus";

export interface MatchedPair {
  indexA: number;
  indexB: number;
  timeA: number;
  timeB: number;
  code: string;
  offset: number;
  offsetBefore: number;
  offsetAfter: number;
  jumpAppliedBefore: boolean;
}

export interface Solution {
  initialOffset: number;
  jumpDirection: JumpDirection;
  jumpIndexA: number | null;
  jumpIndexB: number | null;
  matchesBeforeJump: number;
  pairs: MatchedPair[];
  pairIndices: [number, number][];
}

export interface AdjudicateResponse {
  feasible: boolean;
  matchCount: number;
  minHits: number;
  uniqueness: "unique" | "ambiguous" | null;
  solution: Solution | null;
  witness: Solution | null;
  reason: string | null;
}

export interface Params {
  minOffset: number;
  maxOffset: number;
  jump: number;
  minHits: number;
}

declare global {
  interface Window {
    __ENV__?: {
      apiBase?: string;
    };
  }
}
