// 시험 모드: Figma 없이 Node 로 그리기 계획을 뽑는다.
//   node scripts/plan-cli.ts <storyboard 폴더> [out 파일 이름]
// out/<이름> 에 계획 JSON 을 쓰고, 페이지 · 프레임 · 레이어 개수와 sha256 을 찍는다.
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { plan, count, marksOf, MARK, type Node } from '../src/plan.ts';

const dir = process.argv[2];
if (!dir) { console.error('쓰는 법: node scripts/plan-cli.ts <storyboard 폴더> [이름]'); process.exit(2); }
const sb = JSON.parse(readFileSync(join(dir, 'storyboard.json'), 'utf8'));
const p = plan(sb);
const json = JSON.stringify(p, null, 1) + '\n';
const outDir = join(import.meta.dirname, '..', 'out');
mkdirSync(outDir, { recursive: true });
const outFile = join(outDir, process.argv[3] || 'plan.json');
writeFileSync(outFile, json);

const frames = p.pages[0].kids.filter(n => n.t === 'frame' && n.kids?.[0]?.t === 'image');
const images: Node[] = frames.map(f => f.kids![0]);
const missing = images.filter(i => !existsSync(join(dir, i.src || ''))).map(i => i.src);
const where = sb.original?.where ?? null;
const items = (sb.sheets || []).flatMap((s: any) => s.items || []);
const marks = Object.values(MARK).map(m =>
  `${m} ${items.filter((it: any) => marksOf(it, where).includes(m)).length}`);

console.log(`계획: ${outFile}`);
console.log(`페이지 ${p.pages.length} · 장 프레임 ${frames.length}`);
for (const pg of p.pages) console.log(`  ${pg.name}: 맨 위 노드 ${pg.kids.length} · 레이어 ${count(pg.kids)}`);
console.log(`레이어 합계 ${p.pages.reduce((n, pg) => n + count(pg.kids), 0)}`);
console.log(`표시 (요소 기준): ${marks.join(' · ')}`);
console.log(`그림 없음 ${missing.length}${missing.length ? ' - ' + missing.join(', ') : ''}`);
console.log(`sha256 ${createHash('sha256').update(json).digest('hex')}`);
