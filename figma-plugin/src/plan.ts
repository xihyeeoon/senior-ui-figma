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
// tags: 꼬리표를 합치고 내린 수 한 줄 (끝 메시지에만)
export type Plan = { run: string; pages: Page[]; checks: string[]; warnings: string[]; tags: string };
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
const COL_GAP = 160, ROW_GAP = 160, REVEAL_PAD = 40, REVEAL_HEAD = 32, REVEAL_GAP = 80;
const DEFAULT_SIZE = [390, 844];
const ENTRANCE_NOTE = '과제 밖 입구 = 이 과제에서는 쓰지 않는 메뉴 · 버튼. 옮기거나 접어도 되지만 지우지 않는다 (연구 원칙, 검사 K).';
const SLOT_NOTE = '회색 X 상자 = 그림 (로고 · 아이콘) 이 들어갈 자리. 디자이너가 표준 아이콘 · 로고로 바꾼다.';
const SLOT_FILL = '#E6E6E6', SLOT_LINE = '#8A8A8A', SLOT_MIN_W = 48, SLOT_MIN_H = 28, SLOT_NO_W = 16, SLOT_NO_H = 12;
const NOTICE ='이 와이어프레임은 구조 시안이다. 색 · 모양 · 아이콘 · 로고 · 보안 키패드 모양은 디자이너가 표준 부품으로 채운다.';
const BODY = 14, NAME_MAX = 40;   // 기본 글 크기 · 레이어 이름 최대 글자
const TAG = { size: 11, padX: 6, padY: 2, gap: 4, lift: -10, step: 24 };   // 꼬리표 (4.4): 글 · 안쪽 여백 · 사이 · 위 · 내림

type Shape = { fill: string | null; stroke?: string; dash?: number[]; radius: number;
               align: 'L' | 'C'; inset: number; underline?: boolean };
const SHAPES: Record<string, Shape> = {
  button: { fill: '#F2F2F2', stroke: INK, radius: 8, align: 'C', inset: 4 },
  input:  { fill: PAPER, stroke: INK, radius: 4, align: 'L', inset: 12 },
  a:      { fill: null, radius: 0, align: 'L', inset: 0, underline: true },
  other:  { fill: null, stroke: INK, dash: [4, 4], radius: 0, align: 'C', inset: 4 },
};
const INPUT_TAGS = ['input', 'textarea', 'select'];
const shapeOf = (tag: string) =>
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
  ({ t: 'text', name: chars.slice(0, NAME_MAX), chars, size, ...more });

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

const labelOf = (it: any) => it.text || it.aria || `(${it.action})`;

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
const tags = (labels: string[], w: number): Node => ({ t: 'frame', name: '표시', x: w, y: TAG.lift,
  anchor: 'right', layout: 'H', hug: 'wh', gap: TAG.gap, fill: null, kids: labels.map((k): Node => ({ t: 'frame',
    name: `표시 — ${k}`, layout: 'H', hug: 'wh', pad: [TAG.padY, TAG.padX, TAG.padY, TAG.padX], radius: 4,
    fill: MARK_FILL[k] ?? MARK_FILL[MARK.entrance], kids: [txt(k, TAG.size, { bold: true, color: PAPER })] })) });

// 꼬리표 · 이름표가 겹치는지 보는 데만 쓰는 글 너비 어림 (Noto Sans KR): 한글 · 전각 1, 빈칸 0.25, 그 밖 0.6 × 크기
const textW = (s: string, size: number) => [...s].reduce((a, c) =>
  a + size * (c === ' ' ? 0.25 : c.charCodeAt(0) >= 0x1100 ? 1 : 0.6), 0);
const TAG_H = lineH(TAG.size) + 2 * TAG.padY;
type Box = [number, number, number, number];   // 장 좌표 [x, y, w, h]
const hit = (a: Box, b: Box) => a[0] < b[0] + b[2] && b[0] < a[0] + a[2] && a[1] < b[1] + b[3] && b[1] < a[1] + a[3];
// 장 안의 꼬리표 묶음 (`표시`) 을 그리는 순서로: home = 담은 프레임의 kids, (ox, oy) = 담은 프레임의 장 좌표
type Tags = { node: Node; home: Node[]; ox: number; oy: number };
function tagsIn(nodes: Node[], ox = 0, oy = 0, out: Tags[] = []): Tags[] {
  for (const n of nodes)
    if (n.name === '표시') out.push({ node: n, home: nodes, ox, oy });
    else if (n.t === 'frame' && !n.layout) tagsIn(n.kids || [], ox + n.x!, oy + n.y!, out);
  return out;
}
// 꼬리표 하나하나 (`표시 — …`) 의 장 좌표: 묶음은 오른쪽 끝에 맞춰 왼쪽 → 오른쪽으로 놓인다
const pillWs = (t: Tags) => t.node.kids!.map(p => textW(p.kids![0].chars!, TAG.size) + 2 * TAG.padX);
function pillBoxes(t: Tags): Box[] {
  const ws = pillWs(t), right = t.ox + t.node.x!, y = t.oy + t.node.y!;
  let x = right - ws.reduce((a, b) => a + b, 0) - TAG.gap * (ws.length - 1);
  return ws.map(w => { const b: Box = [x, y, w, TAG_H]; x += w + TAG.gap; return b; });
}
const tagBox = (t: Tags): Box => { const bs = pillBoxes(t), l = bs[bs.length - 1];
  return [bs[0][0], bs[0][1], l[0] + l[2] - bs[0][0], TAG_H]; };

type Tally = { merged: number; into: number; moved: number; pushed: number };
const tallyLine = (n: Tally) => `꼬리표 겹침: 같은 글 ${n.merged}개를 ${n.into}개로 합침`
  + ` · 글이 다른 것과 겹쳐 아래로 내림 ${n.moved} · 무리 이름표를 옆으로 민 것 ${n.pushed}`;

// 한 장 안에서 같은 글의 꼬리표끼리 겹치면 (이어서 겹쳐도) 하나로 합쳐 `{글} · {n}개` 를 가장 왼쪽 요소의
// 자리에 한 번만 둔다 (빈 묶음은 지운다). 그 뒤 묶음끼리 겹치면 뒤 (그리는 순서) 의 것을 한 줄 (24) 씩 내린다.
function untangle(kids: Node[], n: Tally) {
  const all = tagsIn(kids);
  const pills = all.flatMap(t => pillBoxes(t).map((b, i) => ({ t, p: t.node.kids![i], b })));
  const root = pills.map((_, i) => i);
  const find = (i: number): number => root[i] === i ? i : (root[i] = find(root[i]));
  pills.forEach((a, i) => pills.forEach((b, j) => {
    if (j > i && a.p.kids![0].chars === b.p.kids![0].chars && hit(a.b, b.b)) root[find(j)] = find(i);
  }));
  const comps = new Map<number, typeof pills>();
  pills.forEach((x, i) => comps.set(find(i), [...(comps.get(find(i)) || []), x]));
  for (const c of comps.values()) {
    if (c.length < 2) continue;
    const keep = c.reduce((a, x) => x.t.ox < a.t.ox ? x : a), t = keep.p.kids![0];
    t.chars = `${t.chars} · ${c.length}개`; t.name = t.chars.slice(0, NAME_MAX); keep.p.name = `표시 — ${t.chars}`;
    for (const x of c) if (x !== keep) x.t.node.kids!.splice(x.t.node.kids!.indexOf(x.p), 1);
    n.merged += c.length; n.into++;
  }
  for (const t of all) if (!t.node.kids!.length) t.home.splice(t.home.indexOf(t.node), 1);
  const placed: Box[] = [];
  for (const t of all.filter(t => t.node.kids!.length)) {
    if (placed.some(p => hit(p, tagBox(t)))) n.moved++;
    while (placed.some(p => hit(p, tagBox(t)))) t.node.y = t.node.y! + TAG.step;
    placed.push(tagBox(t));
  }
}

// 무리 이름표가 장 안 꼬리표와 겹치면 그 꼬리표 오른쪽 (+4) 으로 민다.
function clearLabels(kids: Node[], groups: Node[], n: Tally) {
  const boxes = tagsIn(kids).map(tagBox);
  for (const g of groups) {
    const t = g.kids!.find(k => k.name === '글')!, w = textW(t.chars!, BODY);
    for (let b; (b = boxes.find(b => hit(b, [g.x! + t.x!, g.y! + t.y!, w, lineH(BODY)])));)
      t.x = b[0] + b[2] + 4 - g.x!, n.pushed++;
  }
}

// 그림 자리 (schema 3 images): 회색 X 상자. (dx, dy) = 담는 프레임의 장 좌표 (요소 안이면 요소 왼쪽 위).
// 큰 상자는 안에 이름 · 크기 두 줄, 작은 상자는 번호만 (아주 작으면 그것도 없음) - 줄지은 작은 로고의
// 글이 서로 겹치지 않게. 이름 · 크기는 주석 그림 절과 레이어 이름으로 찾는다.
// 상자는 자르기 켬이라, 자르기 없는 바깥 프레임에 상자와 '새 그림' 표시를 함께 담는다 (같이 움직인다).
const slotSize = (g: any) => `${Math.round(g.box[2])}×${Math.round(g.box[3])}`;
function slotNode(g: any, dx = 0, dy = 0): Node {
  const [x, y, w, h] = [g.box[0] - dx, g.box[1] - dy, g.box[2], g.box[3]];
  const line = (n: number, path: string): Node => ({ t: 'line', name: `대각선 ${n}`, path, stroke: SLOT_LINE });
  const big = w >= SLOT_MIN_W && h >= SLOT_MIN_H, oy = (h - lineH(10) - lineH(9)) / 2;
  const words: Node[] = big ? [
    txt(g.name, 10, { name: '이름', x: 2, y: oy, w: w - 4, h: lineH(10), color: '#333333', align: 'C', trunc: true }),
    txt(slotSize(g), 9, { name: '크기', x: 2, y: oy + lineH(10), w: w - 4, h: lineH(9), color: '#666666',
      align: 'C', trunc: true })]
    : w >= SLOT_NO_W && h >= SLOT_NO_H ? [txt(String(g.no), 8, { name: '번호', x: 0, y: (h - lineH(8)) / 2, w,
      h: lineH(8), color: '#333333', align: 'C', trunc: true })] : [];
  return { t: 'frame', name: `그림 ${g.no} · ${g.name}`, x, y, w, h, fill: null, clip: false, kids: [
    { t: 'frame', name: '상자', x: 0, y: 0, w, h, fill: SLOT_FILL, stroke: SLOT_LINE, radius: 0, clip: true,
      kids: [line(1, `M 0 0 L ${w} ${h}`), line(2, `M ${w} 0 L 0 ${h}`), ...words] },
    ...(g.original === false ? [tags([NEW_PICTURE], w)] : [])] };
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

// 계획 문맥: 장마다 같은 값 (원본 where · 대응표 · 그림 크기 · 장 이름) 과 장을 그리며 쌓는 것 (꼬리표 셈 · 경고)
type Ctx = { sb: any; where: Record<string, unknown> | null; rn: Map1; dims: Dims; tally: Tally; warnings: string[];
             names: Map<any, string>; titleOf: (screen: string) => string };
// at: 장의 screen · 영역 입구로 센 요소 · 그림 자리. in 이 이 요소인 그림 자리는 요소 좌표로 글 아래에 (같이 움직인다)
function itemNode(c: Ctx, it: any, at: { screen: string; counted: Set<string>; ims: any[] }): Node {
  const [x, y, w, h] = it.box, slots = at.ims.filter(g => g.in === it.no);
  const s = SHAPES[shapeOf(it.tag)];
  const group = it.kind === 'group' && it.group ? ` (${it.group.count}개 묶음)` : '';
  const label = labelOf(it) + group, many = it.kind === 'group';
  // 무리 이름표는 상자 왼쪽 위 바깥 (글 너비에 맞춤) - 상자 안 키 · 칸을 가리지 않게. 꼬리표를 피하는 건 clearLabels
  const kids: Node[] = [...slots.map(g => slotNode(g, x, y)), many
    ? txt(label, BODY, { name: '글', x: 0, y: -lineH(BODY), underline: s.underline })
    : txt(label, BODY, { name: '글', x: s.inset, y: 0, w: Math.max(1, w - 2 * s.inset), h, align: s.align,
        underline: s.underline, trunc: true })];
  const m = marksOf(it, c.where, c.rn, at.screen).filter(k => !(at.counted.has(it.no) && k === MARK.entrance));
  if (m.length) kids.push(tags(m, w));
  // 무리는 채우지 않는다 - 단독 버튼처럼 칠하면 아래 참고 그림 (숫자 키 · 은행 칸) 을 덮는다
  return { t: 'frame', name: `${it.no} ${label}`, x, y, w, h, fill: many ? null : s.fill, stroke: s.stroke,
    dash: many ? [2, 2] : s.dash, radius: s.radius,
    opacity: it.disabled ? 0.4 : 1, clip: false, kids };
}

const revealKey = (s: any) => /^reveal:(.+)$/.exec(s.state || '')?.[1];
// 장 이름: 같은 title 이 둘 이상이면 그 장들만 '· {reveal 키 요소의 글}' (아니면 '· {state}') 을 붙이고,
// 그래도 겹치면 ' ({sheets 순서 번호})'. 주석 · 결과 글 · 바꾼 것 표도 이 이름을 쓴다.
function sheetNames(sheets: any[]): Map<any, string> {
  const many = (names: string[], n: string) => names.filter(k => k === n).length > 1;
  const titles = sheets.map(s => s.title || s.id);
  const first = sheets.map((s, i) => {
    if (!many(titles, titles[i])) return titles[i];
    const key = revealKey(s);
    const it = key && (s.items || []).find((it: any) => it.action === key);
    return `${titles[i]} · ${it ? labelOf(it) : s.state ?? s.id}`;
  });
  return new Map(sheets.map((s, i) => [s, many(first, first[i]) ? `${first[i]} (${i + 1})` : first[i]]));
}

// 펼친 장의 본 장: kind = reveal 이고 state = reveal:<키> 인 장의 of 가 가리키는 장이, 같은 screen 의
// kind = visit 주요 장일 때만. 못 찾으면 null - 그 장은 전체를 그린다.
function baseOf(s: any, byId: Map<string, any>) {
  const b = s.kind === 'reveal' && revealKey(s) ? byId.get(s.of) : null;
  return b?.kind === 'visit' && b.main && b.screen === s.screen ? b : null;
}
// 장 위 한 줄의 이름: 펼침을 연 요소의 글 (키). 연 요소 = flow.reveals 에서 sheet 가 이 장이고 at_sheet 가 본 장인
// 것의 how 마지막 click 의 item (본 장 items 의 no). 못 찾으면 키만. key = false 면 글만 (못 찾으면 '').
function revealName(sb: any, s: any, base: any, key = true) {
  const r = (sb.flow?.reveals || []).find((r: any) => r.sheet === s.id && r.at_sheet === base.id);
  const no = (r?.how || []).filter((h: any) => h.type === 'click' && h.item).pop()?.item;
  const it = (base.items || []).find((it: any) => it.no === no);
  return it ? labelOf(it) + (key ? ` (${revealKey(s)})` : '') : key ? revealKey(s) : '';
}
// 본 장에 없던 것: 키가 같은 것끼리 차례대로 짝짓고, 짝이 남지 않은 것 (자리만 바뀐 것은 짝이 있다)
function fresh(xs: any[] = [], olds: any[] = [], key: (o: any) => string) {
  const left = new Map<string, any[]>();
  for (const o of olds) left.set(key(o), [...(left.get(key(o)) || []), o]);
  return xs.filter(x => !left.get(key(x))?.shift());
}
// 본 장에 없던 요소 (action + 글) · 그림 자리 (name). 키 · box 가 같은 펼친 장끼리 한 무리로 묶는다 (freshKey)
const itKey = (it: any) => `${it.action}|${labelOf(it)}`;
const freshOf = (s: any, base: any) => [...fresh(s.items, base.items, itKey), ...fresh(s.images, base.images, g => g.name)];
const freshKey = (s: any, base: any) => JSON.stringify(freshOf(s, base).map(o => [o.action ? itKey(o) : o.name, o.box]));
// 그것들을 모두 담는 띠 [a, b] - 위아래 40, 장 밖으로는 넘지 않는다. 그런 것이 없으면 null.
function revealCut(s: any, base: any, h: number): [number, number] | null {
  const d = freshOf(s, base);
  if (!d.length) return null;
  return [Math.max(0, Math.floor(Math.min(...d.map(o => o.box[1])) - REVEAL_PAD)),
    Math.min(h, Math.ceil(Math.max(...d.map(o => o.box[1] + o.box[3])) + REVEAL_PAD))];
}

// 띠 [a, b] 에 걸침 (위 끝 < b, 아래 끝 > a) · 띠 좌표로 옮기기 (y − a, box 가 있으면 box 의 y)
const inBand = ([a, b]: [number, number], y: number, h: number) => y < b && y + h > a;
const up = (o: any, a: number) => o.box ? { ...o, box: [o.box[0], o.box[1] - a, o.box[2], o.box[3]] } : { ...o, y: o.y - a };
// 장 프레임 안의 레이어. cut = [a, b] 면 그 띠만: 띠에 걸친 참고 그림 조각 · 요소 · 그림 자리를 y − a 로 옮기고
// 영역 (과 영역 입구 묶기) 은 그리지 않는다.
function sheetKids(c: Ctx, s: any, cut?: [number, number]): Node[] {
  const [w, h] = s.size || DEFAULT_SIZE;
  // 그림 자리: in 이 있는 요소면 그 요소 안, 아니면 (in 이 없는 요소를 가리켜도 - 경고) 장에
  const nos = new Set((s.items || []).map((it: any) => it.no)), imgs: any[] = s.images || [];
  for (const g of imgs) if (g.in && !nos.has(g.in))
    c.warnings.push(`그림 경고: 장 ${s.id} 의 그림 ${g.no} 이 가리키는 요소 ${g.in} 가 없다 — 장에 그렸다`);
  const on = (o: any) => !cut || inBand(cut, o.box[1], o.box[3]);
  const mv = (o: any) => cut ? up(o, cut[0]) : o;
  const its: any[] = (s.items || []).filter(on).map(mv), ims = imgs.map(mv);
  const ent = cut ? { counted: new Set<string>(), regions: new Map<any, number>() } : entranceRegions(s);
  const items: Node[] = its.map(it => itemNode(c, it, { screen: s.screen, counted: ent.counted, ims }));
  const pic = picture(s, w, h, c.dims);
  if (cut) pic.kids = pic.kids!.filter(k => inBand(cut, k.y!, k.h!)).map(k => up(k, cut[0]));
  const kids = [pic, ...imgs.filter(g => !nos.has(g.in) && on(g)).map(g => slotNode(mv(g))),
    ...items, ...(cut ? [] : (s.regions || []).map((r: any) => regionNode(r, ent.regions.get(r))))];
  untangle(kids, c.tally);
  clearLabels(kids, items.filter((_, i) => its[i].kind === 'group'), c.tally);
  return kids;
}

function regionNode(r: any, entrances = 0): Node {
  const [x, y, w, h] = r.box;
  const tag = entrances ? [tags([`과제 밖 입구 · ${entrances} · ${KEEP}`], w)] : [];
  return { t: 'frame', name: `영역 ${r.no} · ${r.name}`, x, y, w, h, fill: null, stroke: '#7A7A7A',
    dash: [6, 4], clip: false, kids: [{ t: 'frame', name: `번호 ${r.no}`, x: 0, y: 0, w: 24, h: 24,
      radius: 12, fill: INK, kids: [txt(String(r.no), 12, { x: 0, y: 0, w: 24, h: 24, bold: true,
        color: PAPER, align: 'C' })] }, ...tag] };
}

function annotation(c: Ctx, sheet: any, title: string): Node[] {
  const out: Node[] = [txt(title, 16, { bold: true }), txt(sheet.purpose || '(목적 없음)', 13)];
  if (sheet.condition) out.push(txt(`조건: ${sheet.condition}`, 12, { color: SUB }));
  out.push(txt('영역', 13, { bold: true }));
  for (const r of sheet.regions || [])
    out.push(txt(`${r.no}. ${r.name} — ${r.description}${r.empty ? ' (빈 영역)' : ''}`, 12));
  if (sheet.images?.length) out.push(txt('그림', 13, { bold: true }), ...sheet.images.map((g: any) =>
    txt(`${g.no} ${g.name} · ${slotSize(g)}${g.original === false ? ` · ${NEW_PICTURE}` : ''}`, 12)));
  out.push(txt('요소', 13, { bold: true }));
  for (const it of sheet.items || []) {
    const m = marksOf(it, c.where, c.rn, sheet.screen).map(k => ` [${k}]`).join('');
    out.push(txt(`${it.no} ${labelOf(it)} → ${said(it.result, c.titleOf)}${m}`, 12));
  }
  return out;
}

// 묶인 펼친 장의 주석 하나: 제목 · 묶인 키 다음, 모두 같은 줄은 한 번, 다른 줄 (조건 등) 은 같은 앞뒤를 한 번 적고
// 가운데를 `{키}` 로 (가운데가 키 그대로가 아니면 아래에 `· {키}: {가운데}` 를 키마다)
function herdAnn(anns: Node[][], keys: string[], title: string): Node[] {
  const out = [txt(title, 16, { bold: true }), txt(`묶인 펼친 장 ${keys.length}: ${keys.join(' · ')}`, 12, { bold: true })];
  for (let i = 1; i < Math.max(...anns.map(a => a.length)); i++) {
    const cs = anns.map(a => a[i]?.chars ?? ''), n0 = anns.find(a => a[i])![i];
    if (cs.every(c => c === cs[0])) { out.push(n0); continue; }
    const m = Math.min(...cs.map(c => c.length)), at = (c: string, j: number) => c[c.length - 1 - j];
    let p = 0, q = 0; while (p < m && cs.every(c => c[p] === cs[0][p])) p++;
    while (q < m - p && cs.every(c => at(c, q) === at(cs[0], q))) q++;
    const mids = cs.map(c => c.slice(p, c.length - q)), one = `${cs[0].slice(0, p)}{키}${cs[0].slice(cs[0].length - q)}`;
    out.push({ ...n0, name: one.slice(0, NAME_MAX), chars: one },
      ...(mids.every((d, j) => d === keys[j]) ? [] : mids.map((d, j) => txt(`· ${keys[j]}: ${d}`, n0.size!))));
  }
  return out;
}

// 세로 자동 배치 · 높이는 내용에 맞춤 (실행 카드 · 주석 · 바꾼 것 표). 안쪽 여백 pad 는 네 방향 같게, 0 이면 두지 않는다
const colFrame = (more: Partial<Node>, pad: number, kids: Node[]): Node =>
  ({ t: 'frame', name: '', layout: 'V', hug: 'h', ...(pad ? { pad: [pad, pad, pad, pad] } : {}), ...more, kids });
function runCard(sb: any, checks: string[]): Node {
  const run = sb.run || {}, orig = run.original || {};
  return colFrame({ name: '실행 카드', x: 0, y: 0, w: CARD_W, gap: 8, fill: PAPER, stroke: INK }, 24, [
      txt(`실행 ${run.id}`, 20, { bold: true }),
      txt(`과제: ${sb.task?.label ?? ''} (${run.task ?? sb.task?.id ?? ''})`, BODY),
      txt(`모델: ${run.model ?? ''}`, BODY),
      txt(`도구 커밋: ${run.commit ?? ''}${run.dirty ? ' (dirty)' : ''}`, BODY),
      txt(`원본: ${orig.path ?? ''} · sha256 ${String(orig.sha256 ?? '').slice(0, 8)}`, BODY),
      txt(`생성: ${sb.generated?.at ?? ''}`, BODY),
      txt(NOTICE, BODY, { bold: true }),
      txt(ENTRANCE_NOTE, BODY),
      ...((sb.sheets || []).some((s: any) => s.images?.length) ? [txt(SLOT_NOTE, BODY)] : []),
      ...checks.map(c => txt(c, BODY)),
    ]);
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
    colFrame({ name: '바꾼 것 표', x: 0, y: 64, w: W, gap: 0, fill: null }, 0, [row(['id', '무엇', '왜', '어느 화면'], true, 0), ...rows])];
}

// 열 (3): 주요 장을 흐름 순서 (flow.steps 의 sheet) 로, 흐름에 없는 주요 장은 sheets 순서로 뒤에.
// 나머지 장은 of 의 열 → 같은 screen 의 주요 장 열 → 새 열. 열 안에서는 sheets 순서
function columns(sb: any, sheets: any[], byId: Map<string, any>, mainOf: Map<string, any>): any[][] {
  const mains: any[] = [];
  for (const st of sb.flow?.steps || []) { const s = byId.get(st.sheet); if (s?.main && !mains.includes(s)) mains.push(s); }
  for (const s of sheets) if (s.main && !mains.includes(s)) mains.push(s);
  const cols: any[][] = mains.map(s => [s]);
  for (const s of sheets) {
    if (s.main) continue;
    const parent = (s.of && byId.get(s.of)?.main) ? byId.get(s.of) : mainOf.get(s.screen);
    const i = mains.indexOf(parent);
    if (i >= 0) cols[i].push(s); else { mains.push(s); cols.push([s]); }
  }
  return cols;
}
// 달라진 것 (키 · box) 이 같은 펼친 장끼리 한 무리 - 무리의 첫 장 자리에 한 번만 그린다 (3.1 같은 펼침 묶기)
function herds(row: any[], base: any): any[][] {
  const same = new Map<string, any[]>();
  for (const s of row) if (freshOf(s, base).length) { const k = freshKey(s, base); same.set(k, [...(same.get(k) || []), s]); }
  return [...same.values()];
}
const annFrame = (title: string, x: number, y: number, kids: Node[]): Node =>
  colFrame({ name: `주석 — ${title}`, x, y, w: ANN_W, gap: ANN_ITEM_GAP, fill: '#FFF8D6' }, ANN_PAD, kids);
// 장 (또는 묶인 펼친 장 무리 g, 첫 장이 대표) 의 이름 · 주석 · 주석 어림 높이
function entry(c: Ctx, g: any[]) {
  const s = g[0], many = g.length > 1, keys = g.map(t => revealKey(t)!);
  const title = many ? `${s.title || s.id} · ${g.length}장 묶음` : c.names.get(s)!;
  const ann = many ? herdAnn(g.map(t => annotation(c, t, c.names.get(t)!)), keys, title) : annotation(c, s, title);
  return { title, ann, annH: estimate(ann, ANN_W - 2 * ANN_PAD, ANN_PAD, ANN_ITEM_GAP) };
}
// 장 위 한 줄의 앞부분: 한 장이면 '{이름} · ', 묶음이면 '{연 요소 글들 · }이 펼침으로 보이는 입구 {n}개: {키들} · '
function revealHead(c: Ctx, g: any[], base: any) {
  if (g.length === 1) return `${revealName(c.sb, g[0], base)} · `;
  const by = [...new Set(g.map(t => revealName(c.sb, t, base, false)).filter(o => o))].map(o => `${o} · `).join('');
  return `${by}이 펼침으로 보이는 입구 ${g.length}개: ${g.map(t => revealKey(t)).join(' · ')} · `;
}
// 펼친 장 한 칸 (3.1): 장 위 한 줄 (넘치면 줄바꿈 - 그만큼 장을 내린다), 장은 본 장과 달라진 띠만, 주석은 장 아래.
// 달라진 것이 없으면 한 줄만. 다음 칸의 rx 와 펼친 장 줄 높이 rowH 를 돌려준다.
function placeReveal(c: Ctx, g: any[], base: any, rx: number, rowH: number) {
  const s = g[0], [w, h] = s.size || DEFAULT_SIZE, e = entry(c, g);
  const cut = revealCut(s, base, h), sw = Math.max(w, ANN_W), head = `펼친 장 — ${revealHead(c, g, base)}`
    + (cut ? `본 장 ${c.names.get(base)} 의 y ${cut[0]}~${cut[1]}` : '본 장과 같음');
  const headH = lineH(BODY) * Math.max(1, Math.ceil(textW(head, BODY) / sw)), top = WF_TOP + headH + REVEAL_HEAD - lineH(BODY);
  const nodes: Node[] = [txt(head, BODY, { name: `펼친 장 — ${e.title}`, x: rx, y: WF_TOP, w: sw, bold: true })];
  if (cut) {
    const fh = cut[1] - cut[0];
    nodes.push({ t: 'frame', name: e.title, x: rx, y: top, w, h: fh, fill: PAPER, clip: true, kids: sheetKids(c, s, cut) },
      annFrame(e.title, rx, top + fh + ANN_GAP, e.ann));
    rowH = Math.max(rowH, top - WF_TOP + fh + ANN_GAP + e.annH);
  } else rowH = Math.max(rowH, headH);
  return { nodes, rx: rx + sw + REVEAL_GAP, rowH };
}
// 아래로 쌓는 장 하나 (3 · 4): 장 프레임과 그 오른쪽 주석. 장 너비와 다음 장의 y 를 돌려준다.
function placeStacked(c: Ctx, s: any, x: number, y: number) {
  const [w, h] = s.size || DEFAULT_SIZE, e = entry(c, [s]);
  const nodes: Node[] = [{ t: 'frame', name: e.title, x, y, w, h, fill: PAPER, clip: true, kids: sheetKids(c, s) },
    annFrame(e.title, x + w + ANN_GAP, y, e.ann)];
  return { nodes, w, y: y + Math.max(h, e.annH) + ROW_GAP };
}

// full: 펼친 장도 전체를 그린다 (플러그인 창의 '펼친 장 전체 그리기')
export function plan(sb: any, dims: Dims = {}, renames: Renames = {}, full = false): Plan {
  const sheets: any[] = sb.sheets || [];
  const where = sb.original?.where ?? null, rn = renames[String(sb.run?.id)] || {};
  const byId = new Map(sheets.map(s => [s.id, s]));
  const mainOf = new Map<string, any>();
  for (const s of sheets) if (s.main && !mainOf.has(s.screen)) mainOf.set(s.screen, s);
  const names = sheetNames(sheets);
  const titleOf = (screen: string) => names.get(mainOf.get(screen)) ?? screen;
  const notes = renameNotes(sheets, where, rn);
  const wf: Node[] = [runCard(sb, notes.checks)];
  const c: Ctx = { sb, where, rn, dims, tally: { merged: 0, into: 0, moved: 0, pushed: 0 }, warnings: notes.warnings,
    names, titleOf };
  let x = 0;
  for (const col of columns(sb, sheets, byId, mainOf)) {
    // 펼친 장 (본 장 = 열 머리) 은 본 장 주석 오른쪽에 가로로 나란히 (같은 펼침은 한 번), 나머지는 아래로
    const row = full ? [] : col.filter(s => baseOf(s, byId) === col[0]), hs = herds(row, col[0]);
    let y = WF_TOP, colW = 0, rx = 0, rowH = 0;
    for (const s of [col[0], ...row, ...col.slice(1).filter(s => !row.includes(s))]) {
      const g = hs.find(g => g.includes(s)) || [s]; if (g[0] !== s) continue;
      if (row.includes(s)) {
        const r = placeReveal(c, g, col[0], rx, rowH);
        wf.push(...r.nodes); rx = r.rx; rowH = r.rowH; colW = Math.max(colW, rx - REVEAL_GAP - x); continue;
      }
      if (rowH) y = Math.max(y, WF_TOP + rowH + ROW_GAP);
      const st = placeStacked(c, s, x, y);
      wf.push(...st.nodes);
      if (s === col[0]) rx = x + st.w + ANN_GAP + ANN_W + REVEAL_GAP;
      y = st.y; colW = Math.max(colW, st.w + ANN_GAP + ANN_W);
    }
    x += colW + COL_GAP;
  }
  const run = String(sb.run?.id ?? 'run');
  return { run, ...notes, tags: tallyLine(c.tally), pages: [{ name: `와이어프레임 · ${run}`, kids: wf },
                        { name: `바꾼 것 · ${run}`, kids: changesPage(sb, titleOf) }] };
}

export function count(nodes: Node[]): number {
  return nodes.reduce((n, k) => n + 1 + count(k.kids || []), 0);
}
