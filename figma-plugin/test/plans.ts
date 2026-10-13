// 시험 입력 → 계획 해시. 원래 해시는 plan-cli 와 같은 직렬화 (JSON.stringify(p, null, 1) + '\n'),
// 키 정렬 해시는 객체 키를 모두 정렬한 뒤 같은 직렬화 - 키 순서만 바뀐 정리를 가려낸다.
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import RENAMES from '../renames.json' with { type: 'json' };
import { plan, count, base, type Dims } from '../src/plan.ts';

export const ROOT = join(import.meta.dirname, '..');
export const sha = (b: string | Buffer) => createHash('sha256').update(b).digest('hex');
const sorted = (v: any): any => Array.isArray(v) ? v.map(sorted) : v && typeof v === 'object'
  ? Object.fromEntries(Object.keys(v).sort().map(k => [k, sorted(v[k])])) : v;
const text = (v: unknown) => JSON.stringify(v, null, 1) + '\n';

// 그림 크기: fixtures 는 dims.json (그림 파일 대신 IHDR 가로 · 세로만), 없으면 plan-cli 처럼 PNG 머리에서
export function dimsOf(dir: string, sb: any): Dims {
  const f = join(dir, 'dims.json');
  if (existsSync(f)) return JSON.parse(readFileSync(f, 'utf8'));
  const dims: Dims = {};
  for (const s of sb.sheets || []) {
    const p = join(dir, s.picture || '');
    if (s.picture && existsSync(p)) { const b = readFileSync(p); dims[base(s.picture)] = [b.readUInt32BE(16), b.readUInt32BE(20)]; }
  }
  return dims;
}

// 입력 sha256 은 줄 끝을 LF 로 맞춘 글로 잰다 - git 의 autocrlf 가 작업 사본만 CRLF 로 바꿔도 같은 입력이다
const fileSha = (f: string) => sha(readFileSync(f, 'utf8').replace(/\r\n/g, '\n'));
export function inputSha(dir: string) {
  const f = join(ROOT, dir), d = join(f, 'dims.json');
  return { storyboard: fileSha(join(f, 'storyboard.json')), dims: existsSync(d) ? fileSha(d) : null };
}
export const renamesSha = () => fileSha(join(ROOT, 'renames.json'));

export function hashes(dir: string, full: boolean) {
  const f = join(ROOT, dir), sb = JSON.parse(readFileSync(join(f, 'storyboard.json'), 'utf8'));
  const p = plan(sb, dimsOf(f, sb), RENAMES, full);
  return { plain: sha(text(p)), sorted: sha(text(sorted(p))),
    layers: p.pages.reduce((n, pg) => n + count(pg.kids), 0), tags: p.tags };
}
