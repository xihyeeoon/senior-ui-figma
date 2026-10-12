// 시험 모드: Figma 없이 Node 로 그리기 계획을 뽑는다.
//   node scripts/plan-cli.ts <storyboard 폴더> [out 파일 이름]
// out/<이름> 에 계획 JSON 을 쓰고, 페이지 · 프레임 · 레이어 개수와 sha256 을 찍는다.
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import RENAMES from '../renames.json' with { type: 'json' };
import { plan, count, marksOf, tiles, base, MARK, MAX_PX, type Node, type Dims } from '../src/plan.ts';

const dir = process.argv[2];
if (!dir) { console.error('쓰는 법: node scripts/plan-cli.ts <storyboard 폴더> [이름]'); process.exit(2); }
const sb = JSON.parse(readFileSync(join(dir, 'storyboard.json'), 'utf8'));
// 그림 크기는 PNG 머리 (IHDR 의 가로 · 세로) 에서 읽는다 - UI 가 재는 것과 같은 값
const dims: Dims = {};
for (const s of sb.sheets || []) {
  const f = join(dir, s.picture || '');
  if (s.picture && existsSync(f)) { const b = readFileSync(f); dims[base(s.picture)] = [b.readUInt32BE(16), b.readUInt32BE(20)]; }
}
const p = plan(sb, dims, RENAMES);
const json = JSON.stringify(p, null, 1) + '\n';
const outDir = join(import.meta.dirname, '..', 'out');
mkdirSync(outDir, { recursive: true });
const outFile = join(outDir, process.argv[3] || 'plan.json');
writeFileSync(outFile, json);

const frames = p.pages[0].kids.filter(n => n.t === 'frame' && n.kids?.[0]?.t === 'group');
const pics: Node[] = frames.map(f => f.kids![0]);
const missing = pics.filter(i => !existsSync(join(dir, i.src || ''))).map(i => i.src);
const where = sb.original?.where ?? null;
const rn = (RENAMES as any)[sb.run?.id] || {};
const marked = (sb.sheets || []).flatMap((s: any) => (s.items || []).map((it: any) =>
  ({ it, s, m: marksOf(it, where, rn, s.screen) })));
const marks = Object.values(MARK).map(m => { const hit = marked.filter((x: any) => x.m.includes(m));
  return `${m} ${hit.length} (action ${new Set(hit.map((x: any) => x.it.action)).size})`; });

console.log(`계획: ${outFile}`);
console.log(`페이지 ${p.pages.length} · 장 프레임 ${frames.length}`);
for (const pg of p.pages) console.log(`  ${pg.name}: 맨 위 노드 ${pg.kids.length} · 레이어 ${count(pg.kids)}`);
console.log(`레이어 합계 ${p.pages.reduce((n, pg) => n + count(pg.kids), 0)}`);
console.log(`표시 (요소 기준, action 종류): ${marks.join(' · ')}`);
const fresh = new Map<string, Set<string>>();
for (const x of marked) if (x.m.includes(MARK.fresh)) fresh.set(x.it.action, (fresh.get(x.it.action) || new Set()).add(x.s.id));
for (const [a, ids] of fresh) console.log(`  새 요소: ${a} · ${[...ids].join(', ')}`);
for (const l of [...p.checks, ...p.warnings]) console.log(l);
const big = Object.values(dims).filter(([w, h]) => w > MAX_PX || h > MAX_PX).length;
console.log(`그림 ${Object.keys(dims).length} · ${MAX_PX}px 초과 ${big} · 조각 합계 ${pics.reduce((n, g) => n + g.kids!.length, 0)}`);
for (const [f, [w, h]] of Object.entries(dims)) console.log(`  ${f} ${w}×${h} → 조각 ${tiles(w, h).length}`);
console.log(`그림 없음 ${missing.length}${missing.length ? ' - ' + missing.join(', ') : ''}`);
console.log(`sha256 ${createHash('sha256').update(json).digest('hex')}`);
