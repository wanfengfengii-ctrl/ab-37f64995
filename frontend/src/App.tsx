import { useMemo, useState } from "react";
import type { AdjudicateResponse, Event, Params } from "./types";
import { adjudicate, ApiError } from "./api";
import { validateStream } from "./parse";
import { StreamEditor } from "./StreamEditor";
import { SolutionView } from "./SolutionView";

const SAMPLE_A: Event[] = [
  { time: 100, code: "TRIG" },
  { time: 250, code: "BEAM" },
  { time: 400, code: "DIAG" },
  { time: 760, code: "BEAM" },
  { time: 910, code: "DIAG" },
];

const SAMPLE_B: Event[] = [
  { time: 100, code: "TRIG" },
  { time: 250, code: "BEAM" },
  { time: 400, code: "DIAG" },
  { time: 455, code: "NOISE" },
  { time: 755, code: "BEAM" },
  { time: 905, code: "DIAG" },
];

type NumField = keyof Params;

export default function App() {
  const [streamA, setStreamA] = useState<Event[]>(SAMPLE_A);
  const [streamB, setStreamB] = useState<Event[]>(SAMPLE_B);
  const [params, setParams] = useState<Params>({
    minOffset: -20,
    maxOffset: 20,
    jump: 5,
    minHits: 3,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AdjudicateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const localErrors = useMemo(
    () => [
      ...validateStream(streamA, "流 A"),
      ...validateStream(streamB, "流 B"),
      ...(params.maxOffset < params.minOffset
        ? ["偏移上限必须 ≥ 下限"]
        : []),
      ...(params.jump < 0 ? ["固定跳变量不能为负"] : []),
    ],
    [streamA, streamB, params],
  );

  function setParam(field: NumField, raw: string) {
    setParams((p) => ({ ...p, [field]: Number(raw) }));
  }

  async function run() {
    if (localErrors.length) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await adjudicate(streamA, streamB, params);
      setResult(r);
    } catch (e) {
      if (e instanceof ApiError && e.details) {
        setError(`${e.message}\n${JSON.stringify(e.details, null, 2)}`);
      } else {
        setError((e as Error).message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <h1>加速器束流脉冲复核台</h1>
        <p className="subtitle">
          两条事件流 · 保序同码配对 · 初始偏移范围内至多一次永久 ±J 跳变 ·
          先最大化匹配数再按规范序裁决
        </p>
      </header>

      <div className="grid2">
        <StreamEditor
          title="事件流 A（采集卡 1）"
          accent="a"
          events={streamA}
          onChange={setStreamA}
        />
        <StreamEditor
          title="事件流 B（采集卡 2）"
          accent="b"
          events={streamB}
          onChange={setStreamB}
        />
      </div>

      <section className="card params">
        <h2>裁决参数</h2>
        <div className="param-grid">
          <label>
            初始偏移下限
            <input
              type="number"
              value={params.minOffset}
              onChange={(e) => setParam("minOffset", e.target.value)}
            />
          </label>
          <label>
            初始偏移上限
            <input
              type="number"
              value={params.maxOffset}
              onChange={(e) => setParam("maxOffset", e.target.value)}
            />
          </label>
          <label>
            固定跳变量 J ≥ 0
            <input
              type="number"
              min={0}
              value={params.jump}
              onChange={(e) => setParam("jump", e.target.value)}
            />
          </label>
          <label>
            最低命中数
            <input
              type="number"
              min={1}
              max={80}
              value={params.minHits}
              onChange={(e) => setParam("minHits", e.target.value)}
            />
          </label>
        </div>
        <div className="run-bar">
          <button
            className="btn primary big"
            onClick={run}
            disabled={loading || localErrors.length > 0}
          >
            {loading ? "裁决中…" : "发起裁决"}
          </button>
          {localErrors.length > 0 && (
            <ul className="err-list inline">
              {localErrors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {error && <pre className="card error-box">{error}</pre>}

      {result && (
        <ResultPanel result={result} jump={params.jump} />
      )}
    </div>
  );
}

function ResultPanel({
  result,
  jump,
}: {
  result: AdjudicateResponse;
  jump: number;
}) {
  return (
    <section className="card verdict">
      <header className="card-head">
        <h2>裁决结果</h2>
        {result.feasible ? (
          <span
            className={`badge verdict-badge ${
              result.uniqueness === "unique" ? "unique" : "ambiguous"
            }`}
          >
            {result.uniqueness === "unique" ? "唯一解" : "存在歧义"}
          </span>
        ) : (
          <span className="badge verdict-badge infeasible">无解</span>
        )}
      </header>

      <p className="summary">
        最大匹配数 <strong>{result.matchCount}</strong>，最低命中要求{" "}
        <strong>{result.minHits}</strong>。
      </p>

      {!result.feasible && (
        <p className="reason">判无解原因：{result.reason}</p>
      )}

      {result.feasible && result.solution && (
        <>
          {result.uniqueness === "ambiguous" && (
            <p className="reason warn">
              规范首解并非唯一：下方第二份见证方案达到相同最大匹配数，但初始偏移 /
              跳变方式 / 跳变前匹配数 / 配对索引序列不同。
            </p>
          )}
          <SolutionView
            title="规范首解"
            badge="FIRST"
            sol={result.solution}
            jump={jump}
          />
          {result.witness && (
            <SolutionView
              title="歧义见证（规范序第二份）"
              badge="WITNESS"
              sol={result.witness}
              jump={jump}
            />
          )}
        </>
      )}
    </section>
  );
}
