import type { Solution } from "./types";

const DIR_LABEL: Record<Solution["jumpDirection"], string> = {
  none: "无跳变",
  plus: "加（+J）",
  minus: "减（−J）",
};

export function SolutionView({
  title,
  badge,
  sol,
  jump,
}: {
  title: string;
  badge: string;
  sol: Solution;
  jump: number;
}) {
  return (
    <section className="card solution">
      <header className="card-head">
        <h2>{title}</h2>
        <span className={`badge badge-${sol.jumpDirection}`}>{badge}</span>
      </header>

      <dl className="meta-grid">
        <div>
          <dt>初始偏移 d₀</dt>
          <dd>{sol.initialOffset}</dd>
        </div>
        <div>
          <dt>跳变方式</dt>
          <dd>{DIR_LABEL[sol.jumpDirection]}</dd>
        </div>
        <div>
          <dt>跳变后偏移 d₁</dt>
          <dd>
            {sol.jumpDirection === "none"
              ? "—"
              : sol.jumpDirection === "plus"
                ? sol.initialOffset + jump
                : sol.initialOffset - jump}
          </dd>
        </div>
        <div>
          <dt>跳变前匹配数</dt>
          <dd>{sol.matchesBeforeJump}</dd>
        </div>
        <div>
          <dt>配对总数</dt>
          <dd>{sol.pairs.length}</dd>
        </div>
      </dl>

      <div className="table-wrap">
        <table className="pairs">
          <thead>
            <tr>
              <th>序</th>
              <th>A 索引</th>
              <th>B 索引</th>
              <th>tA</th>
              <th>tB</th>
              <th>事件码</th>
              <th>跳变前偏移</th>
              <th>跳变后偏移</th>
              <th>时段</th>
              <th>对时校验</th>
            </tr>
          </thead>
          <tbody>
            {sol.pairs.map((p, k) => {
              const boundary =
                sol.matchesBeforeJump > 0 && k === sol.matchesBeforeJump - 1;
              return (
                <tr
                  key={k}
                  className={
                    boundary
                      ? "jump-boundary"
                      : p.jumpAppliedBefore
                        ? "post-jump"
                        : ""
                  }
                >
                  <td className="idx">{k + 1}</td>
                  <td>{p.indexA}</td>
                  <td>{p.indexB}</td>
                  <td className="num">{p.timeA}</td>
                  <td className="num">{p.timeB}</td>
                  <td className="code">{p.code}</td>
                  <td className="num">{p.offsetBefore}</td>
                  <td className="num">{p.offsetAfter}</td>
                  <td>
                    {p.jumpAppliedBefore ? (
                      <span className="tag post">跳变后</span>
                    ) : boundary ? (
                      <span className="tag boundary">跳变前末对</span>
                    ) : (
                      <span className="tag pre">跳变前</span>
                    )}
                  </td>
                  <td className="ok">
                    {p.timeA === p.timeB + p.offsetBefore ||
                    p.timeA === p.timeB + p.offsetAfter ? (
                      "✓ 完全相等"
                    ) : (
                      "✗"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
