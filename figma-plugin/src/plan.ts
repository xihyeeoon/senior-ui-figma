// storyboard.json → 그리기 계획. Figma API 도, 네트워크도, 시각도 쓰지 않는다 - 같은
// 파일은 언제나 같은 계획이 된다. 숫자는 모두 RULES.md 와 같다 (바꾸면 둘 다 고친다).

export type Node = {
  t: 'frame' | 'text' | 'image' | 'group' | 'line';
  name: string;
  x?: number; y?: number; w?: number; h?: number;
  fill?: string | null; stroke?: string; dash?: number[]; radius?: number;
  opacity?: number; locked?: boolean; clip?: boolean;
  layout?: 'V' | 'H'; gap?: number; pad?: number[]; // pad = [위, 오른쪽, 아래, 왼쪽]
  hug?: 'h' | 'wh';          // 자동 배치 프레임이 높이만 / 너비 · 높이 모두 내용에 맞춘다
  anchor?: 'right';          // x 가 오른쪽 끝 (그린 뒤 너비만큼 왼쪽으로)
  chars?: string; size?: number; bold?: boolean; color?: string;
  align?: 'L' | 'C'; underline?: boolean; trunc?: boolean;
  src?: string;              // image: storyboard 폴더 기준 그림 경로 (+ `#조각 번호`)
  sheet?: string;            // group: 어느 장의 그림인지 (알림에 쓴다)
  path?: string;             // line: 선 하나의 SVG 경로 (노드 왼쪽 위 기준)
  kids?: Node[];
};
export type Page = { name: string; kids: Node[] };
// checks · warnings: 대응표 확인 · 경고 줄 (끝 메시지와 실행 카드에 그대로 옮긴다)
export type Plan = { run: string; pages: Page[]; checks: string[]; warnings: string[] };
export type Dims = Record<string, [number, number]>;   // 그림 파일 이름 → [가로, 세로] px
// renames.json: run.id → { 생성 action → 값 | { sheet.screen → 값 } }, 값 = 원본 action | 'new' | 'made-pressable'
// (연구자가 적는다, RENAMES.md)
type Val = string | Record<string, string>;
export type Renames = Record<string, Record<string, Val>>;
type Map1 = Record<string, Val>;
const valOf = (rn: Map1, action: string, screen: string): string | undefined => {
  const v = rn[action]; return typeof v === 'string' ? v : v?.[screen];
};
const SPECIAL = ['new', 'made-pressable'];

const INK = '#000000', PAPER = '#FFFFFF', SUB = '#555555';
// 입구 꼬리표 글은 연구 원칙 '보여 주는 방식은 자유, 사용자가 할 수 있는 일은 줄이지 않는다' 에서 왔다.
// 꼬리표는 짧게, 뜻은 실행 카드의 ENTRANCE_NOTE 에 한 번 적는다.
const KEEP = '지우지 말 것';
export const MARK = { entrance: `과제 밖 입구 · ${KEEP}`, none: '누르면 변화 없음 — 확인 필요', fresh: '새 요소',
  pressable: '새 동작 (원본에선 누를 수 없던 글)' };
const NEW_PICTURE = '새 그림';
const MARK_FILL: Record<string, string> = {
  [MARK.entrance]: '#6B6B6B', [MARK.none]: '#D9480F', [MARK.fresh]: '#1C64F2',
  [MARK.pressable]: '#1C64F2', [NEW_PICTURE]: '#1C64F2' };
const REF_NAME = '참고 — 로우파이 그림', REF_OPACITY = 0.4;
export const MAX_PX = 4096;   // Figma createImage 가 받는 가로 · 세로 최대 (ui.html 과 같다)
const CARD_W = 720, WF_TOP = 400;
const ANN_GAP = 24, ANN_W = 360, ANN_PAD = 16, ANN_ITEM_GAP = 6;
const COL_GAP = 160, ROW_GAP = 160;
const DEFAULT_SIZE = [390, 844];
const ENTRANCE_NOTE = '과제 밖 입구 = 이 과제에서는 쓰지 않는 메뉴 · 버튼. 옮기거나 접어도 되지만 지우지 않는다 (연구 원칙, 검사 K).';
const SLOT_NOTE = '회색 X 상자 = 그림 (로고 · 아이콘) 이 들어갈 자리. 디자이너가 표준 아이콘 · 로고로 바꾼다.';
const SLOT_FILL = '#E6E6E6', SLOT_LINE = '#8A8A8A', SLOT_MIN_W = 48, SLOT_MIN_H = 28;
const NOTICE ='이 와이어프레임은 구조 시안이다. 색 · 모양 · 아이콘 · 로고 · 보안 키패드 모양은 디자이너가 표준 부품으로 채운다.';

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

// 그림 자르기: 위→아래 줄마다 왼쪽→오른쪽, 조각 하나는 가로 · 세로 MAX_PX 이하 (ui.html 과 같다)
const cuts = (n: number) => { const a: number[][] = [];
  for (let p = 0; p < n; p += MAX_PX) a.push([p, Math.min(MAX_PX, n - p)]); return a; };
export const tiles = (w: number, h: number) =>
  cuts(h).flatMap(([y, th]) => cuts(w).map(([x, tw]) => [x, y, tw, th]));
export const base = (s: string) => s.split('/').pop() || s;

// 참고 그림 그룹: 조각마다 사각형 하나, 장 좌표 = 픽셀 ÷ 배율. 고른 그림의 크기를 모르면
// 장 크기 × scale 을 그림 크기로 본다 (그 그림은 어차피 '그림 없음' 회색이 된다).
function picture(s: any, w: number, h: number, dims: Dims): Node {
  const [pw, ph] = dims[base(s.picture || '')] || [w * (s.scale || 1), h * (s.scale || 1)];
  const k = s.scale || pw / w, ts = tiles(pw, ph);
  return { t: 'group', name: REF_NAME, sheet: s.id, src: s.picture, opacity: REF_OPACITY,
    locked: true, kids: ts.map(([x, y, tw, th], i): Node => ({ t: 'image', name: `조각 ${i + 1}/${ts.length}`,
      x: x / k, y: y / k, w: tw / k, h: th / k, src: `${s.picture}#${i + 1}` })) };
}

export const labelOf = (it: any) => it.text || it.aria || `(${it.action})`;

// 새 요소: 대응표 값이 'new' · 'made-pressable' 이면 그대로, 원본 action 이면 새 요소가 아니다
// (where 에 없어도 - 그건 renameNotes 가 '대응표 확인' 으로 알린다). 값이 없으면 where 로 본다.
export function marksOf(it: any, where: Record<string, unknown> | null, rn: Map1 = {}, screen = ''): string[] {
  const m: string[] = [], to = valOf(rn, it.action, screen);
  if (it.entrance === true) m.push(MARK.entrance);
  if (it.result?.kind === 'none') m.push(MARK.none);
  if (to === 'made-pressable') m.push(MARK.pressable);
  else if (to === 'new' || (to === undefined && where && !(it.action in where))) m.push(MARK.fresh);
  return m;
}

// 대응표 점검. 확인: 원본 action 이 원본을 걷는 동안 보이지 않았다 (where 에 없음).
// 경고: storyboard.json 에 없는 생성 action, 또는 그 action 이 나온 장의 sheet.screen 이 아닌 화면 키.
function renameNotes(sheets: any[], where: Record<string, unknown> | null, rn: Map1) {
  const seen = new Map<string, Set<string>>();   // 생성 action → 나온 sheet.screen
  for (const s of sheets) for (const it of s.items || [])
    seen.set(it.action, (seen.get(it.action) || new Set()).add(s.screen));
  const checks: string[] = [], warnings: string[] = [];
  for (const [a, v] of Object.entries(rn)) {
    const on = seen.get(a);
    if (!on) { warnings.push(`대응표 경고: ${a} 는 storyboard.json 에 없는 생성 action 이다`); continue; }
    const vals = typeof v === 'string' ? [v] : Object.entries(v).filter(([sc]) => on.has(sc) || !warnings.push(
      `대응표 경고: ${a} 의 화면 ${sc} 는 그 요소가 나온 장의 sheet.screen 이 아니다 (${[...on].join(', ')})`)).map(e => e[1]);
    for (const o of new Set(vals)) if (where && !SPECIAL.includes(o) && !(o in where))
      checks.push(`대응표 확인: ${a} → ${o} 은 원본을 걷는 동안 보이지 않았다 (원본 HTML 에는 있음 — 연구자 확인)`);
  }
  return { checks, warnings };
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

// 꼬리표 묶음: 오른쪽 끝이 x = w, 위가 -10. 글 색은 MARK_FILL (영역 입구 꼬리표는 입구 색)
const tags = (labels: string[], w: number): Node => ({ t: 'frame', name: '표시', x: w, y: -10,
  anchor: 'right', layout: 'H', hug: 'wh', gap: 4, fill: null, kids: labels.map((k): Node => ({ t: 'frame',
    name: `표시 — ${k}`, layout: 'H', hug: 'wh', pad: [2, 6, 2, 6], radius: 4,
    fill: MARK_FILL[k] ?? MARK_FILL[MARK.entrance], kids: [txt(k, 11, { bold: true, color: PAPER })] })) });

// 그림 자리 (schema 3 images): 회색 X 상자. (dx, dy) = 담는 프레임의 장 좌표 (요소 안이면 요소 왼쪽 위).
// 상자는 자르기 켬이라 작은 상자의 글 (상자 아래 바깥) 과 '새 그림' 표시는 상자 밖 형제로 둔다.
const slotSize = (g: any) => `${Math.round(g.box[2])}×${Math.round(g.box[3])}`;
function slotNodes(g: any, dx = 0, dy = 0): Node[] {
  const [x, y, w, h] = [g.box[0] - dx, g.box[1] - dy, g.box[2], g.box[3]];
  const small = w < SLOT_MIN_W || h < SLOT_MIN_H;
  const words = (pre: string, ox: number, oy: number, tw?: number): Node[] => [
    txt(g.name, 10, { name: `${pre}이름`, x: ox, y: oy, w: tw, h: tw && lineH(10), color: '#333333',
      align: 'C', trunc: true }),
    txt(slotSize(g), 9, { name: `${pre}크기`, x: ox, y: oy + lineH(10), w: tw, h: tw && lineH(9),
      color: '#666666', align: 'C', trunc: true })];
  const line = (n: number, path: string): Node => ({ t: 'line', name: `대각선 ${n}`, path, stroke: SLOT_LINE });
  return [{ t: 'frame', name: `그림 ${g.no} · ${g.name}`, x, y, w, h, fill: SLOT_FILL, stroke: SLOT_LINE,
      radius: 0, clip: true, kids: [line(1, `M 0 0 L ${w} ${h}`), line(2, `M ${w} 0 L 0 ${h}`),
        ...(small ? [] : words('', 2, (h - lineH(10) - lineH(9)) / 2, w - 4))] },
    ...(small ? words(`그림 ${g.no} `, x, y + h + 2) : []),
    ...(g.original === false ? [{ ...tags([NEW_PICTURE], w), x: x + w, y: y - 10 }] : [])];
}

// 요소가 모두 입구인 영역: 영역 → 처음 세는 요소 수. 그 요소들은 요소 꼬리표에서 입구를 뺀다.
function entranceRegions(s: any) {
  const byNo = new Map((s.items || []).map((it: any) => [it.no, it]));
  const counted = new Set<string>(), regions = new Map<any, number>();
  for (const r of s.regions || []) {
    const els: string[] = r.elements || [];
    if (!els.length || !els.every(e => (byNo.get(e) as any)?.entrance === true)) continue;
    const fresh = els.filter(e => !counted.has(e));
    fresh.forEach(e => counted.add(e));
    if (fresh.length) regions.set(r, fresh.length);
  }
  return { counted, regions };
}

// slots: in 이 이 요소인 그림 자리 - 요소 좌표로 옮겨 글 아래에 둔다 (요소와 같이 움직인다)
function itemNode(it: any, where: Record<string, unknown> | null, rn: Map1, screen: string, grouped: boolean,
                  slots: any[] = []): Node {
  const [x, y, w, h] = it.box;
  const s = SHAPES[shapeOf(it.tag)];
  const group = it.kind === 'group' && it.group ? ` (${it.group.count}개 묶음)` : '';
  const label = labelOf(it) + group;
  const kids: Node[] = [...slots.flatMap(g => slotNodes(g, x, y)), txt(label, 14, { name: '글', x: s.inset,
    y: 0, w: Math.max(1, w - 2 * s.inset), h, align: s.align, underline: s.underline, trunc: true })];
  const m = marksOf(it, where, rn, screen).filter(k => !(grouped && k === MARK.entrance));
  if (m.length) kids.push(tags(m, w));
  return { t: 'frame', name: `${it.no} ${label}`, x, y, w, h, fill: s.fill, stroke: s.stroke,
    dash: it.kind === 'group' ? [2, 2] : s.dash, radius: s.radius,
    opacity: it.disabled ? 0.4 : 1, clip: false, kids };
}

// 장 이름: 같은 title 이 둘 이상이면 그 장들만 '· {reveal 키 요소의 글}' (아니면 '· {state}') 을 붙이고,
// 그래도 겹치면 ' ({sheets 순서 번호})'. 주석 · 결과 글 · 바꾼 것 표도 이 이름을 쓴다.
function sheetNames(sheets: any[]): Map<any, string> {
  const many = (names: string[], n: string) => names.filter(k => k === n).length > 1;
  const titles = sheets.map(s => s.title || s.id);
  const first = sheets.map((s, i) => {
    if (!many(titles, titles[i])) return titles[i];
    const key = /^reveal:(.+)$/.exec(s.state || '')?.[1];
    const it = key && (s.items || []).find((it: any) => it.action === key);
    return `${titles[i]} · ${it ? labelOf(it) : s.state ?? s.id}`;
  });
  return new Map(sheets.map((s, i) => [s, many(first, first[i]) ? `${first[i]} (${i + 1})` : first[i]]));
}

function regionNode(r: any, entrances = 0): Node {
  const [x, y, w, h] = r.box;
  const tag = entrances ? [tags([`과제 밖 입구 · ${entrances} · ${KEEP}`], w)] : [];
  return { t: 'frame', name: `영역 ${r.no} · ${r.name}`, x, y, w, h, fill: null, stroke: '#7A7A7A',
    dash: [6, 4], clip: false, kids: [{ t: 'frame', name: `번호 ${r.no}`, x: 0, y: 0, w: 24, h: 24,
      radius: 12, fill: INK, kids: [txt(String(r.no), 12, { x: 0, y: 0, w: 24, h: 24, bold: true,
        color: PAPER, align: 'C' })] }, ...tag] };
}

function annotation(sheet: any, title: string, where: Record<string, unknown> | null, rn: Map1,
                    titleOf: (s: string) => string): Node[] {
  const out: Node[] = [txt(title, 16, { bold: true }), txt(sheet.purpose || '(목적 없음)', 13)];
  if (sheet.condition) out.push(txt(`조건: ${sheet.condition}`, 12, { color: SUB }));
  out.push(txt('영역', 13, { bold: true }));
  for (const r of sheet.regions || [])
    out.push(txt(`${r.no}. ${r.name} — ${r.description}${r.empty ? ' (빈 영역)' : ''}`, 12));
  if (sheet.images?.length) out.push(txt('그림', 13, { bold: true }), ...sheet.images.map((g: any) =>
    txt(`${g.no} ${g.name} · ${slotSize(g)}${g.original === false ? ` · ${NEW_PICTURE}` : ''}`, 12)));
  out.push(txt('요소', 13, { bold: true }));
  for (const it of sheet.items || []) {
    const m = marksOf(it, where, rn, sheet.screen).map(k => ` [${k}]`).join('');
    out.push(txt(`${it.no} ${labelOf(it)} → ${said(it.result, titleOf)}${m}`, 12));
  }
  return out;
}

function runCard(sb: any, checks: string[]): Node {
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
      txt(ENTRANCE_NOTE, 14),
      ...((sb.sheets || []).some((s: any) => s.images?.length) ? [txt(SLOT_NOTE, 14)] : []),
      ...checks.map(c => txt(c, 14)),
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

export function plan(sb: any, dims: Dims = {}, renames: Renames = {}): Plan {
  const sheets: any[] = sb.sheets || [];
  const where = sb.original?.where ?? null, rn = renames[String(sb.run?.id)] || {};
  const byId = new Map(sheets.map(s => [s.id, s]));
  const mainOf = new Map<string, any>();
  for (const s of sheets) if (s.main && !mainOf.has(s.screen)) mainOf.set(s.screen, s);
  const names = sheetNames(sheets);
  const titleOf = (screen: string) => names.get(mainOf.get(screen)) ?? screen;

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

  const notes = renameNotes(sheets, where, rn);
  const wf: Node[] = [runCard(sb, notes.checks)];
  let x = 0;
  for (const col of cols) {
    let y = WF_TOP, colW = 0;
    for (const s of col) {
      const [w, h] = s.size || DEFAULT_SIZE, title = names.get(s)!;
      const ann = annotation(s, title, where, rn, titleOf);
      const ent = entranceRegions(s);
      const annH = estimate(ann, ANN_W - 2 * ANN_PAD, ANN_PAD, ANN_ITEM_GAP);
      // 그림 자리: in 이 있는 요소면 그 요소 안, 아니면 (in 이 없는 요소를 가리켜도 - 경고) 장에
      const nos = new Set((s.items || []).map((it: any) => it.no)), imgs: any[] = s.images || [];
      for (const g of imgs) if (g.in && !nos.has(g.in))
        notes.warnings.push(`그림 경고: 장 ${s.id} 의 그림 ${g.no} 이 가리키는 요소 ${g.in} 가 없다 — 장에 그렸다`);
      wf.push({ t: 'frame', name: title, x, y, w, h, fill: PAPER, clip: true, kids: [
        picture(s, w, h, dims),
        ...imgs.filter(g => !nos.has(g.in)).flatMap(g => slotNodes(g)),
        ...(s.items || []).map((it: any) => itemNode(it, where, rn, s.screen, ent.counted.has(it.no),
          imgs.filter(g => g.in === it.no))),
        ...(s.regions || []).map((r: any) => regionNode(r, ent.regions.get(r)))] });
      wf.push({ t: 'frame', name: `주석 — ${title}`, x: x + w + ANN_GAP, y, w: ANN_W, layout: 'V',
        hug: 'h', pad: [ANN_PAD, ANN_PAD, ANN_PAD, ANN_PAD], gap: ANN_ITEM_GAP, fill: '#FFF8D6', kids: ann });
      y += Math.max(h, annH) + ROW_GAP;
      colW = Math.max(colW, w + ANN_GAP + ANN_W);
    }
    x += colW + COL_GAP;
  }
  const run = String(sb.run?.id ?? 'run');
  return { run, ...notes, pages: [{ name: `와이어프레임 · ${run}`, kids: wf },
                        { name: `바꾼 것 · ${run}`, kids: changesPage(sb, titleOf) }] };
}

export function count(nodes: Node[]): number {
  return nodes.reduce((n, k) => n + 1 + count(k.kids || []), 0);
}
