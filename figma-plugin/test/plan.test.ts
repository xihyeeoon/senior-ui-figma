// 계획이 golden.json 과 같은지 (그림이 바뀌지 않았는지) 본다. npm test.
// 입력 sha256 이 다르면 '입력이 바뀜' 으로 실패 - 계획 탓과 구분한다. 기대 해시는 손으로 고치지 않는다.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { ROOT, hashes, inputSha, renamesSha } from './plans.ts';

type Golden = { renames_sha256: string; inputs: { name: string; path: string; input_sha256: unknown;
  normal: string; full: string; sorted: { normal: string; full: string }; layers: { normal: number; full: number } }[] };
const golden: Golden = JSON.parse(readFileSync(join(ROOT, 'golden.json'), 'utf8'));

test('입력: renames.json', () => assert.equal(renamesSha(), golden.renames_sha256, '입력이 바뀜: renames.json'));

for (const g of golden.inputs) test(`계획: ${g.name}`, () => {
  assert.deepEqual(inputSha(g.path), g.input_sha256, `입력이 바뀜: ${g.path}`);
  for (const mode of ['normal', 'full'] as const) {
    const h = hashes(g.path, mode === 'full');
    assert.equal(h.layers, g.layers[mode], `${g.name} ${mode} 레이어 수`);
    assert.equal(h.sorted, g.sorted[mode], `${g.name} ${mode} 키 정렬 해시`);
    assert.equal(h.plain, g[mode], `${g.name} ${mode} 원래 해시`);
    assert.deepEqual(hashes(g.path, mode === 'full'), h, `${g.name} ${mode} 두 번 돌린 계획이 다름`);
  }
});

test('가짜 입력 push: 무리 이름표 밀기를 지난다', () => {
  const pushed = Number(/무리 이름표를 옆으로 민 것 (\d+)/.exec(hashes('fixtures/push', false).tags)?.[1]);
  assert.ok(pushed >= 1, `민 것 ${pushed}`);
});
