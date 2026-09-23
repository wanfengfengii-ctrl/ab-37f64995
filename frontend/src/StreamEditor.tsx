import { useMemo, useRef, useState } from "react";
import type { Event } from "./types";
import { parseStreamText, streamToText, validateStream } from "./parse";

interface Props {
  title: string;
  accent: string;
  events: Event[];
  onChange: (events: Event[]) => void;
}

export function StreamEditor({ title, accent, events, onChange }: Props) {
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [importMsg, setImportMsg] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const errors = useMemo(() => validateStream(events, title), [events, title]);

  function update(idx: number, field: keyof Event, raw: string) {
    const next = events.map((e, i) =>
      i === idx
        ? field === "time"
          ? { ...e, time: Number(raw) }
          : { ...e, code: raw.toUpperCase() }
        : e,
    );
    onChange(next);
  }

  function addRow() {
    if (events.length >= 80) return;
    const last = events.length ? events[events.length - 1].time : -1;
    onChange([...events, { time: last + 1, code: "A" }]);
  }

  function removeRow(idx: number) {
    onChange(events.filter((_, i) => i !== idx));
  }

  function applyImport() {
    const { events: parsed, errors: errs } = parseStreamText(importText);
    setImportMsg(errs);
    if (errs.length === 0) {
      onChange(parsed);
      setImportOpen(false);
    }
  }

  function loadFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      setImportText(text);
      const { events: parsed, errors: errs } = parseStreamText(text);
      setImportMsg(errs);
      if (errs.length === 0) {
        onChange(parsed);
        setImportOpen(false);
      }
    };
    reader.readAsText(file);
  }

  return (
    <section className={`card stream stream-${accent}`}>
      <header className="card-head">
        <h2>{title}</h2>
        <span className="count">
          {events.length} 事件
          {errors.length === 0 ? " ✓" : ""}
        </span>
      </header>

      {errors.length > 0 && (
        <ul className="err-list">
          {errors.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>时间 (t)</th>
              <th>事件码</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, idx) => (
              <tr key={idx}>
                <td className="idx">{idx}</td>
                <td>
                  <input
                    type="number"
                    value={Number.isFinite(e.time) ? e.time : ""}
                    min={0}
                    max={10 ** 12}
                    onChange={(ev) => update(idx, "time", ev.target.value)}
                  />
                </td>
                <td>
                  <input
                    className="code-input"
                    value={e.code}
                    maxLength={8}
                    onChange={(ev) => update(idx, "code", ev.target.value)}
                  />
                </td>
                <td>
                  <button
                    className="btn-mini"
                    onClick={() => removeRow(idx)}
                    title="删除此行"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row-actions">
        <button className="btn" onClick={addRow} disabled={events.length >= 80}>
          ＋ 添加事件
        </button>
        <button
          className="btn"
          onClick={() => {
            setImportText(streamToText(events));
            setImportMsg([]);
            setImportOpen((v) => !v);
          }}
        >
          {importOpen ? "收起导入" : "导入 / 批量编辑"}
        </button>
        <button className="btn" onClick={() => fileRef.current?.click()}>
          上传文件
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.csv,text/plain"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) loadFile(f);
            e.target.value = "";
          }}
        />
      </div>

      {importOpen && (
        <div className="import-box">
          <p className="hint">每行一条：「时间 事件码」或「时间,事件」，# 开头为注释。</p>
          <textarea
            rows={8}
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            spellCheck={false}
          />
          {importMsg.length > 0 && (
            <ul className="err-list">
              {importMsg.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          )}
          <div>
            <button className="btn primary" onClick={applyImport}>
              应用到 {title}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
