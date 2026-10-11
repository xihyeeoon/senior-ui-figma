// Figma 쪽: UI 가 넘긴 storyboard.json 과 그림으로 plan() 의 계획을 그대로 그린다.
// 판단은 plan.ts 에만 있다 - 여기서는 노드를 만들고 칸을 옮겨 적을 뿐이다.
import { plan, lineH, count, base, type Node, type Dims } from './plan.ts';

const PLUGIN_KEY = 'storyboard-run';
// images: `{파일 이름}#{조각 번호}` → PNG 조각, dims: 파일 이름 → 원본 [가로, 세로] px
type Msg = { storyboard: string; images: Record<string, Uint8Array>; dims: Dims };

figma.showUI(__html__, { width: 380, height: 320 });

let FONT: FontName = { family: 'Noto Sans KR', style: 'Regular' };
let BOLD: FontName = { family: 'Noto Sans KR', style: 'Bold' };
async function loadFonts() {
  try { await Promise.all([figma.loadFontAsync(FONT), figma.loadFontAsync(BOLD)]); }
  catch {
    FONT = { family: 'Inter', style: 'Regular' }; BOLD = { family: 'Inter', style: 'Bold' };
    await Promise.all([figma.loadFontAsync(FONT), figma.loadFontAsync(BOLD)]);
  }
}

function rgb(hex: string): RGB {
  const n = parseInt(hex.slice(1), 16);
  return { r: (n >> 16 & 255) / 255, g: (n >> 8 & 255) / 255, b: (n & 255) / 255 };
}
const solid = (hex?: string | null): Paint[] => hex ? [{ type: 'SOLID', color: rgb(hex) }] : [];

let missingPictures: string[] = [];

function drawText(n: Node, layout?: 'V' | 'H'): TextNode {
  const t = figma.createText();
  t.fontName = n.bold ? BOLD : FONT;
  t.characters = n.chars || '';
  t.fontSize = n.size || 14;
  t.lineHeight = { value: lineH(n.size || 14), unit: 'PIXELS' };
  t.fills = solid(n.color || '#000000');
  t.textAlignHorizontal = n.align === 'C' ? 'CENTER' : 'LEFT';
  if (n.underline) t.textDecoration = 'UNDERLINE';
  if (layout === 'V') t.textAutoResize = 'HEIGHT';            // 너비는 붙인 뒤 STRETCH
  else if (n.w !== undefined && n.h !== undefined) {
    t.resize(n.w, n.h); t.textAutoResize = 'NONE'; t.textAlignVertical = 'CENTER';
    if (n.trunc) t.textTruncation = 'ENDING';
  } else if (n.w !== undefined) { t.resize(n.w, lineH(n.size || 14)); t.textAutoResize = 'HEIGHT'; }
  else t.textAutoResize = 'WIDTH_AND_HEIGHT';
  return t;
}

// 참고 그림: 조각 사각형을 장 프레임에 붙인 뒤 묶는다. 조각이 하나라도 없으면 모두 회색.
function drawPicture(n: Node, parent: ChildrenMixin & BaseNode, images: Msg['images']): GroupNode {
  const bytes = n.kids!.map(k => images[base(k.src || '')]);
  const have = bytes.every(b => b);
  if (!have) missingPictures.push(n.src || '(경로 없음)');
  const rects = n.kids!.map((k, i) => {
    const r = figma.createRectangle();
    r.name = k.name; r.resize(k.w!, k.h!); parent.appendChild(r); r.x = k.x!; r.y = k.y!;
    r.fills = have ? [{ type: 'IMAGE', imageHash: figma.createImage(bytes[i]).hash, scaleMode: 'FILL' }]
      : solid('#EEEEEE');
    return r;
  });
  const g = figma.group(rects, parent);
  g.name = n.name; g.opacity = n.opacity ?? 1; g.locked = n.locked === true;
  return g;
}

function drawFrame(n: Node): FrameNode {
  const f = figma.createFrame();
  f.resize(n.w ?? 1, n.h ?? 1);
  f.fills = solid(n.fill);
  f.strokes = solid(n.stroke);
  if (n.stroke) f.strokeWeight = 1;
  if (n.dash) f.dashPattern = n.dash;
  f.cornerRadius = n.radius || 0;
  f.clipsContent = n.clip === true;
  if (n.layout) {
    f.layoutMode = n.layout === 'V' ? 'VERTICAL' : 'HORIZONTAL';
    f.itemSpacing = n.gap || 0;
    const [pt, pr, pb, pl] = n.pad || [0, 0, 0, 0];
    f.paddingTop = pt; f.paddingRight = pr; f.paddingBottom = pb; f.paddingLeft = pl;
    // V: 높이가 주축 / H: 너비가 주축. hug 'h' 는 높이만, 'wh' 는 둘 다 내용에 맞춘다
    const hugW = n.hug === 'wh', hugH = n.hug === 'h' || n.hug === 'wh';
    f.primaryAxisSizingMode = (n.layout === 'V' ? hugH : hugW) ? 'AUTO' : 'FIXED';
    f.counterAxisSizingMode = (n.layout === 'V' ? hugW : hugH) ? 'AUTO' : 'FIXED';
  }
  return f;
}

function draw(n: Node, parent: ChildrenMixin & BaseNode, images: Msg['images'], layout?: 'V' | 'H'): SceneNode {
  if (n.t === 'group') return drawPicture(n, parent, images);
  const node: SceneNode = n.t === 'text' ? drawText(n, layout) : drawFrame(n);
  node.name = n.name;
  parent.appendChild(node);
  if (n.t === 'frame') for (const k of n.kids || []) draw(k, node as FrameNode, images, n.layout);
  if (layout === 'V' && node.type === 'TEXT') node.layoutAlign = 'STRETCH';
  if (!layout) {
    node.x = n.anchor === 'right' ? (n.x || 0) - node.width : (n.x || 0);
    node.y = n.y || 0;
  }
  if (n.opacity !== undefined) node.opacity = n.opacity;
  if (n.locked) node.locked = true;
  return node;
}

figma.ui.onmessage = async (msg: Msg) => {
  try {
    const sb = JSON.parse(msg.storyboard);
    const p = plan(sb, msg.dims || {});
    await loadFonts();
    missingPictures = [];
    // 같은 실행을 다시 불러오면 지우고 다시 그린다 - 새 페이지를 먼저 만든 뒤 옛 것을 지운다
    const old = figma.root.children.filter(pg => pg.getPluginData(PLUGIN_KEY) === p.run);
    const made: PageNode[] = [];
    for (const pg of p.pages) {
      const page = figma.createPage();
      page.name = pg.name;
      page.setPluginData(PLUGIN_KEY, p.run);
      for (const n of pg.kids) draw(n, page, msg.images);
      made.push(page);
    }
    await figma.setCurrentPageAsync(made[0]);
    for (const pg of old) pg.remove();
    const card = made[0].children[0];
    if (card) figma.viewport.scrollAndZoomIntoView([card]);
    const layers = p.pages.reduce((s, pg) => s + count(pg.kids), 0);
    figma.ui.postMessage({ ok: true, text: `다 그렸다 - 페이지 ${made.length} · 레이어 ${layers}`
      + ` · 지운 옛 페이지 ${old.length} · 그림 없음 ${missingPictures.length}`
      + (missingPictures.length ? ` (${missingPictures.join(', ')})` : '') });
  } catch (e) {
    figma.ui.postMessage({ ok: false, text: `그리지 못했다 - ${(e as Error).message || e}` });
  }
};
