# 걷기 시험 (헤드리스 chromium, 창 390x844)

- 시작 화면: s01
- steps: s01 하나뿐 (s01 에서 나가는 이동이 없다)
- s01 에서 눌러서 닿는 화면: s01
- 닿지 않는 화면: s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13

## 이동마다 (그 화면을 띄우고 눌러 봄)

| 이동 | 누른 것 | 결과 | 짝 |
|---|---|---|---|
| s02 → s03 | `[data-action='a-s02-06']` | 됨 | 02.png → 03.png |
| s03 → s04 | `[data-action='a-s03-04']` | 됨 | 03.png → 04.png |
| s04 → s05 | `[data-action='a-s04-05']` | 됨 | 04.png → 05a.png |
| s05 → s06 | `[data-action='a-s05-03']` | 됨 | 05c.png → 06a.png |
| s07 → s08 | `[data-action='a-s07-06']` | 됨 | 07.png → 07a.png |
| s08 → s09 | `[data-action='a-s08-10']` | 됨 | 07a.png → 08.png |
| s09 → s10 | `[data-action='a-s09-05']` | 됨 | 08.png → 09a.png |
| s13 → s12 | `[data-action='a-s13-01']` | 됨 | 오류 화면에서 되돌아감 (10.png → 11.png 의 반대) |

## 오류 경로

- e1: s13 에서 recover → s12 (됨)
