// storyboard.json → 그리기 계획. Figma API 도, 네트워크도, 시각도 쓰지 않는다 - 같은
// 파일은 언제나 같은 계획이 된다. 숫자는 모두 RULES.md 와 같다 (바꾸면 둘 다 고친다).

export type Node = {
  t: 'frame' | 'text' | 'image';
  name: string;
  x?: number; y?: number; w?: number; h?: number;
  fill?: string | null; stroke?: string; dash?: number[]; radius?: number;
  opacity?: number; locked?: boolean; clip?: boolean;
  layout?: 'V' | 'H'; gap?: number; pad?: number[]; // pad = [위, 오른쪽, 아래, 왼쪽]
  hug?: 'h' | 'wh';          // 자동 배치 프레임이 높이만 / 너비 · 높이 모두 내용에 맞춘다
  anchor?: 'right';          // x 가 오른쪽 끝 (그린 뒤 너비만큼 왼쪽으로)
  chars?: string; size?: number; bold?: boolean; color?: string;
  align?: 'L' | 'C'; underline?: boolean; trunc?: boolean;
  src?: string;              // image: storyboard 폴더 기준 그림 경로
  kids?: Node[];
};
export type Page = { name: string; kids: Node[] };
export type Plan = { run: string; pages: Page[] };

const INK = '#000000', PAPER = '#FFFFFF', SUB = '#555555';
export const MARK = { entrance: '과제 밖 입구', none: '누르면 변화 없음 — 확인 필요', fresh: '새 요소' };
const MARK_FILL: Record<string, string> = {
  [MARK.entrance]: '#6B6B6B', [MARK.none]: '#D9480F', [MARK.fresh]: '#1C64F2' };
const REF_NAME = '참고 — 로우파이 그림', REF_OPACITY = 0.4;
const CARD_W = 720, WF_TOP = 400;
const ANN_GAP = 24, ANN_W = 360, ANN_PAD = 16, ANN_ITEM_GAP = 6;
const COL_GAP = 160, ROW_GAP = 160;
const DEFAULT_SIZE = [390, 844];
const NOTICE = '이 와이어프레임은 구조 시안이다. 색 · 모양 · 아이콘 · 로고 · 보안 키패드 모양은 디자이너가 표준 부품으로 채운다.';

type Shape = { fill: string | null; stroke?: string; dash?: number[]; radius: number;
               align: 'L' | 'C'; inset: number; underline?: boolean };
const SHAPES: Record<string, Shape> = {
  button: { fill: '#F2F2F2', stroke: INK, radius: 8, align: 'C', inset: 4 },
  input:  { fill: PAPER, stroke: INK, radius: 4, align: 'L', inset: 12 },
  a:      { fill: null, radius: 0, align: 'L', inset: 0, underline: true },
  other:  { fill: null, stroke: INK, dash: [4, 4], radius: 0, align: 'C', inset: 4 },
};
const INPUT_TAGS = ['input', 'textarea', 'select'];
export const shapeOf = (tag: string) =>
  tag === 'button' || tag === 'a' ? tag : INPUT_TAGS.includes(tag) ? 'input' : 'other';

export const lineH = (size: number) => Math.round(size * 1.5);

// 자동 배치 열의 높이 어림 - 아래로 쌓는 장끼리 겹치지 않게 하는 데만 쓴다.
function estimate(texts: Node[], innerW: number, pad: number, gap: number) {
  let h = pad * 2 + gap * Math.max(0, texts.length - 1);
  for (const t of texts) {
    const perLine = Math.max(1, Math.floor(innerW / t.size!));
    h += Math.max(1, Math.ceil(t.chars!.length / perLine)) * lineH(t.size!);
  }
  return h;
}

const txt = (chars: string, size: number, more: Partial<Node> = {}): Node =>
  ({ t: 'text', name: chars.slice(0, 40), chars, size, ...more });

export const labelOf = (it: any) => it.text || it.aria || `(${it.action})`;

export function marksOf(it: any, where: Record<string, unknown> | null): string[] {
  const m: string[] = [];
  if (it.entrance === true) m.push(MARK.entrance);
  if (it.result?.kind === 'none') m.push(MARK.none);
  if (where && !(it.action in where)) m.push(MARK.fresh);
  return m;
}

function said(r: any, titleOf: (s: string) => string) {
  switch (r?.kind) {
    case 'screen': return `${titleOf(r.to)} 화면으로`;
    case 'same': return `같은 화면 — ${r.detail ?? ''}`;
    case 'none': return '보이는 변화 없음';
    case 'disabled': return '꺼져 있어 누르지 않음';
    case 'failed': return `누르지 못함 — ${r.detail ?? ''}`;
    default: return '결과 없음';
  }
}

function itemNode(it: any, where: Record<string, unknown> | null): Node {
  const [x, y, w, h] = it.box;
  const s = SHAPES[shapeOf(it.tag)];
  const group = it.kind === 'group' && it.group ? ` (${it.group.count}개 묶음)` : '';
  const label = labelOf(it) + group;
  const kids: Node[] = [txt(label, 14, { name: '글', x: s.inset, y: 0, w: Math.max(1, w - 2 * s.inset),
    h, align: s.align, underline: s.underline, trunc: true })];
  const m = marksOf(it, where);
  if (m.length) kids.push({ t: 'frame', name: '표시', x: w, y: -10, anchor: 'right', layout: 'H',
    hug: 'wh', gap: 4, fill: null, kids: m.map((k): Node => ({ t: 'frame', name: `표시 — ${k}`,
      layout: 'H', hug: 'wh', pad: [2, 6, 2, 6], radius: 4, fill: MARK_FILL[k],
      kids: [txt(k, 11, { bold: true, color: PAPER })] })) });
  return { t: 'frame', name: `${it.no} ${label}`, x, y, w, h, fill: s.fill, stroke: s.stroke,
    dash: it.kind === 'group' ? [2, 2] : s.dash, radius: s.radius,
    opacity: it.disabled ? 0.4 : 1, clip: false, kids };
}

function regionNode(r: any): Node {
  const [x, y, w, h] = r.box;
  return { t: 'frame', name: `영역 ${r.no} · ${r.name}`, x, y, w, h, fill: null, stroke: '#7A7A7A',
    dash: [6, 4], clip: false, kids: [{ t: 'frame', name: `번호 ${r.no}`, x: 0, y: 0, w: 24, h: 24,
      radius: 12, fill: INK, kids: [txt(String(r.no), 12, { x: 0, y: 0, w: 24, h: 24, bold: true,
        color: PAPER, align: 'C' })] }] };
}

function annotation(sheet: any, title: string, where: Record<string, unknown> | null,
                    titleOf: (s: string) => string): Node[] {
  const out: Node[] = [txt(title, 16, { bold: true }), txt(sheet.purpose || '(목적 없음)', 13)];
  if (sheet.condition) out.push(txt(`조건: ${sheet.condition}`, 12, { color: SUB }));
  out.push(txt('영역', 13, { bold: true }));
  for (const r of sheet.regions || [])
    out.push(txt(`${r.no}. ${r.name} — ${r.description}${r.empty ? ' (빈 영역)' : ''}`, 12));
  out.push(txt('요소', 13, { bold: true }));
  for (const it of sheet.items || []) {
    const m = marksOf(it, where).map(k => ` [${k}]`).join('');
    out.push(txt(`${it.no} ${labelOf(it)} → ${said(it.result, titleOf)}${m}`, 12));
  }
  return out;
}

function runCard(sb: any): Node {
  const run = sb.run || {}, orig = run.original || {};
  return { t: 'frame', name: '실행 카드', x: 0, y: 0, w: CARD_W, layout: 'V', hug: 'h',
    pad: [24, 24, 24, 24], gap: 8, fill: PAPER, stroke: INK, kids: [
      txt(`실행 ${run.id}`, 20, { bold: true }),
      txt(`과제: ${sb.task?.label ?? ''} (${run.task ?? sb.task?.id ?? ''})`, 14),
      txt(`모델: ${run.model ?? ''}`, 14),
      txt(`도구 커밋: ${run.commit ?? ''}${run.dirty ? ' (dirty)' : ''}`, 14),
      txt(`원본: ${orig.path ?? ''} · sha256 ${String(orig.sha256 ?? '').slice(0, 8)}`, 14),
      txt(`생성: ${sb.generated?.at ?? ''}`, 14),
      txt(NOTICE, 14, { bold: true }),
    ] };
}

function changesPage(sb: any, titleOf: (s: string) => string): Node[] {
  const widths = [60, 560, 380, 200], gap = 16, pad = 8;
  const W = widths.reduce((a, b) => a + b) + gap * (widths.length - 1) + pad * 2;
  const row = (cells: string[], bold: boolean, i: number): Node => ({ t: 'frame',
    name: bold ? '머리줄' : cells[0], w: W, layout: 'H', hug: 'h', pad: [pad, pad, pad, pad], gap,
    fill: bold ? '#F2F2F2' : PAPER, stroke: '#CCCCCC',
    kids: cells.map((c, j) => txt(c, 13, { name: `${['id', '무엇', '왜', '어느 화면'][j]} ${i}`,
      w: widths[j], bold })) });
  const rows = (sb.changes || []).map((c: any, i: number) => row([c.id, c.what, c.why,
    (c.to_screens || []).map(titleOf).join(', ')], false, i + 1));
  return [txt(`바꾼 것 — ${sb.task?.label ?? ''} · ${sb.run?.id ?? ''}`, 20, { x: 0, y: 0, bold: true }),
    { t: 'frame', name: '바꾼 것 표', x: 0, y: 64, w: W, layout: 'V', hug: 'h', gap: 0, fill: null,
      kids: [row(['id', '무엇', '왜', '어느 화면'], true, 0), ...rows] }];
}

export function plan(sb: any): Plan {
  const sheets: any[] = sb.sheets || [];
  const where = sb.original?.where ?? null;
  const byId = new Map(sheets.map(s => [s.id, s]));
  const mainOf = new Map<string, any>();
  for (const s of sheets) if (s.main && !mainOf.has(s.screen)) mainOf.set(s.screen, s);
  const titleOf = (screen: string) => mainOf.get(screen)?.title || screen;

  // 1. 주요 장: 흐름 순서 (flow.steps 의 sheet), 흐름에 없는 주요 장은 sheets 순서로 뒤에
  const mains: any[] = [];
  for (const st of sb.flow?.steps || []) {
    const s = byId.get(st.sheet);
    if (s?.main && !mains.includes(s)) mains.push(s);
  }
  for (const s of sheets) if (s.main && !mains.includes(s)) mains.push(s);
  const cols: any[][] = mains.map(s => [s]);
  // 2. 나머지 장: of 의 열 → 같은 screen 의 주요 장 열 → 새 열. 열 안에서는 sheets 순서
  for (const s of sheets) {
    if (s.main) continue;
    const parent = (s.of && byId.get(s.of)?.main) ? byId.get(s.of) : mainOf.get(s.screen);
    const i = mains.indexOf(parent);
    if (i >= 0) cols[i].push(s); else { mains.push(s); cols.push([s]); }
  }

  const wf: Node[] = [runCard(sb)];
  let x = 0;
  for (const col of cols) {
    let y = WF_TOP, colW = 0;
    for (const s of col) {
      const [w, h] = s.size || DEFAULT_SIZE, title = s.title || s.id;
      const ann = annotation(s, title, where, titleOf);
      const annH = estimate(ann, ANN_W - 2 * ANN_PAD, ANN_PAD, ANN_ITEM_GAP);
      wf.push({ t: 'frame', name: title, x, y, w, h, fill: PAPER, clip: true, kids: [
        { t: 'image', name: REF_NAME, x: 0, y: 0, w, h, src: s.picture, opacity: REF_OPACITY, locked: true },
        ...(s.items || []).map((it: any) => itemNode(it, where)),
        ...(s.regions || []).map(regionNode)] });
      wf.push({ t: 'frame', name: `주석 — ${title}`, x: x + w + ANN_GAP, y, w: ANN_W, layout: 'V',
        hug: 'h', pad: [ANN_PAD, ANN_PAD, ANN_PAD, ANN_PAD], gap: ANN_ITEM_GAP, fill: '#FFF8D6', kids: ann });
      y += Math.max(h, annH) + ROW_GAP;
      colW = Math.max(colW, w + ANN_GAP + ANN_W);
    }
    x += colW + COL_GAP;
  }
  const run = String(sb.run?.id ?? 'run');
  return { run, pages: [{ name: `와이어프레임 · ${run}`, kids: wf },
                        { name: `바꾼 것 · ${run}`, kids: changesPage(sb, titleOf) }] };
}

export function count(nodes: Node[]): number {
  return nodes.reduce((n, k) => n + 1 + count(k.kids || []), 0);
}
