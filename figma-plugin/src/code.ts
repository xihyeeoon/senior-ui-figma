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

let missingPictures: string[] = [], failedSheets: string[] = [];

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

// 참고 그림: 조각 사각형을 장 프레임에 붙인 뒤 묶는다. 조각이 하나라도 없거나 createImage 가
// 실패하면 그 장의 조각은 모두 회색으로 두고 계속 그린다.
function imagePaints(n: Node, images: Msg['images']): Paint[][] | null {
  const bytes = n.kids!.map(k => images[base(k.src || '')]);
  if (!bytes.every(b => b)) { missingPictures.push(n.src || '(경로 없음)'); return null; }
  try { return bytes.map(b => [{ type: 'IMAGE', imageHash: figma.createImage(b).hash, scaleMode: 'FILL' }]); }
  catch { failedSheets.push(n.sheet || n.src || '?'); return null; }
}

function drawPicture(n: Node, parent: ChildrenMixin & BaseNode, images: Msg['images']): GroupNode {
  const paints = imagePaints(n, images);
  const rects = n.kids!.map((k, i) => {
    const r = figma.createRectangle();
    r.name = k.name; r.resize(k.w!, k.h!); parent.appendChild(r); r.x = k.x!; r.y = k.y!;
    r.fills = paints ? paints[i] : solid('#EEEEEE');
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
  const made: PageNode[] = [];
  try {
    const sb = JSON.parse(msg.storyboard);
    const p = plan(sb, msg.dims || {});
    await loadFonts();
    missingPictures = []; failedSheets = [];
    // 같은 실행을 다시 불러오면 지우고 다시 그린다 - 새 페이지를 먼저 만든 뒤 옛 것을 지운다
    const old = figma.root.children.filter(pg => pg.getPluginData(PLUGIN_KEY) === p.run);
    for (const pg of p.pages) {
      const page = figma.createPage();
      made.push(page);                                         // 도중에 멈춰도 치울 수 있게 먼저 적는다
      page.name = pg.name;
      page.setPluginData(PLUGIN_KEY, p.run);
      for (const n of pg.kids) draw(n, page, msg.images);
    }
    await figma.setCurrentPageAsync(made[0]);
    const card = made[0].children[0];
    if (card) figma.viewport.scrollAndZoomIntoView([card]);
    const pages = made.splice(0);    // 여기부터 새 페이지는 완성 - 옛 것을 지우다 멈춰도 남긴다
    for (const pg of old) pg.remove();
    const layers = p.pages.reduce((s, pg) => s + count(pg.kids), 0);
    figma.ui.postMessage({ ok: true, text: `다 그렸다 - 페이지 ${pages.length} · 레이어 ${layers}`
      + ` · 지운 옛 페이지 ${old.length} · 그림 없음 ${missingPictures.length}`
      + (missingPictures.length ? ` (${missingPictures.join(', ')})` : '')
      + ` · 그림 실패 ${failedSheets.length}` + (failedSheets.length ? ` (장 id ${failedSheets.join(', ')})` : '') });
  } catch (e) {
    // 이번에 만든 새 페이지만 지운다 - 옛 페이지는 그대로. 보고 있는 페이지는 지울 수 없어 먼저 옮긴다.
    const keep = figma.root.children.find(pg => !made.includes(pg));
    if (keep && made.includes(figma.currentPage)) await figma.setCurrentPageAsync(keep);
    for (const pg of made) if (!pg.removed) pg.remove();
    figma.ui.postMessage({ ok: false, text: `그리지 못했다 - ${(e as Error).message || e}` });
  }
};
