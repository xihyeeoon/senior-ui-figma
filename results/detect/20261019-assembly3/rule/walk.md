# 걷기 시험 (헤드리스 chromium, 창 390x844)

- 시작 화면: s01
- steps: s01 → (skipped-states) s02 → (tap) s03 → (tap) s04 → (tap) s05 → (tap) s06 → (skipped-states) s07 → (tap) s08 → (tap) s09 → (tap) s10 → (keypad-advance) s11 → (keypad-advance) s12
- s01 에서 눌러서 닿는 화면: s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12
- 닿지 않는 화면: s13

## 이동마다 (그 화면을 띄우고 눌러 봄)

| 이동 | via | 누른 것 | 결과 | 짝 |
|---|---|---|---|---|
| s01 → s02 | skipped-states | `[data-action='a-s01-07']` | 됨 | 01c.png → 02.png |
| s02 → s03 | tap | `[data-action='a-s02-06']` | 됨 | 02.png → 03.png |
| s03 → s04 | tap | `[data-action='a-s03-04']` | 됨 | 03.png → 04.png |
| s04 → s05 | tap | `[data-action='a-s04-05']` | 됨 | 04.png → 05a.png |
| s05 → s06 | tap | `[data-action='a-s05-03']` | 됨 | 05c.png → 06a.png |
| s06 → s07 | skipped-states | `[data-action='a-s06-02']` | 됨 | 06c.png → 07.png |
| s07 → s08 | tap | `[data-action='a-s07-06']` | 됨 | 07.png → 07a.png |
| s08 → s09 | tap | `[data-action='a-s08-10']` | 됨 | 07a.png → 08.png |
| s09 → s10 | tap | `[data-action='a-s09-05']` | 됨 | 08.png → 09a.png |
| s10 → s11 | keypad-advance | `[data-action='a-s10-g1'][data-v='8']` | 됨 | 09a.png → 09b.png |
| s11 → s12 | keypad-advance | `[data-action='a-s11-g1'][data-v='8']` | 됨 | 09b.png → 10.png |
| s13 → s12 | error-recover | `[data-action='a-s13-01']` | 됨 | 오류 화면에서 되돌아감 (10.png → 11.png 의 반대) |

- keypad-advance 숫자 키마다 눌러 넘어간 수: s10 → s11 10/10, s11 → s12 10/10
- keypad-advance 숫자 아닌 키를 눌러 그 화면에 머문 수: s10 2/2, s11 2/2

## 오류 경로

- e1: s13 에서 recover → s12 (됨)
