import type { Event } from "./types";

const CODE_RE = /^[A-Z0-9]{1,8}$/;

/** Parse an import text block: one event per line, "time code" or "time,code". */
export function parseStreamText(text: string): { events: Event[]; errors: string[] } {
  const events: Event[] = [];
  const errors: string[] = [];
  const lines = text.split(/\r?\n/);
  lines.forEach((raw, idx) => {
    const line = raw.trim();
    if (!line || line.startsWith("#")) return;
    const parts = line.split(/[\s,]+/).filter(Boolean);
    if (parts.length !== 2) {
      errors.push(`第 ${idx + 1} 行格式无效：应为「时间 事件码」`);
      return;
    }
    const [timeStr, codeRaw] = parts;
    const time = Number(timeStr);
    const code = codeRaw.toUpperCase();
    if (!Number.isInteger(time) || time < 0 || time > 10 ** 12) {
      errors.push(`第 ${idx + 1} 行时间无效：${timeStr}（需为 0…10^12 整数）`);
      return;
    }
    if (!CODE_RE.test(code)) {
      errors.push(`第 ${idx + 1} 行事件码无效：${codeRaw}（1-8 位大写字母或数字）`);
      return;
    }
    events.push({ time, code });
  });

  for (let i = 1; i < events.length; i++) {
    if (events[i].time <= events[i - 1].time) {
      errors.push(`时间必须严格递增：第 ${i + 1} 条 ${events[i].time} 不大于前一条`);
      break;
    }
  }
  return { events, errors };
}

export function streamToText(events: Event[]): string {
  return events.map((e) => `${e.time} ${e.code}`).join("\n");
}

export function validateStream(events: Event[], label: string): string[] {
  const errors: string[] = [];
  if (events.length < 2 || events.length > 80) {
    errors.push(`${label}需含 2–80 个事件，当前 ${events.length} 个`);
  }
  for (let i = 0; i < events.length; i++) {
    const e = events[i];
    if (!Number.isInteger(e.time) || e.time < 0 || e.time > 10 ** 12) {
      errors.push(`${label}第 ${i + 1} 条时间非法（需为 0…10^12 整数）`);
      break;
    }
    if (!CODE_RE.test(e.code)) {
      errors.push(`${label}第 ${i + 1} 条事件码非法：${e.code}`);
      break;
    }
  }
  for (let i = 1; i < events.length; i++) {
    if (
      Number.isInteger(events[i].time) &&
      Number.isInteger(events[i - 1].time) &&
      events[i].time <= events[i - 1].time
    ) {
      errors.push(`${label}时间必须严格递增（位置 ${i + 1}）`);
      break;
    }
  }
  return errors;
}
