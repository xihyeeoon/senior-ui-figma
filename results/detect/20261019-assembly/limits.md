# 조립 1단계 - 한계 (이번 실행)

## 못 이은 흐름 짝 (이동을 만들지 않음)

| 짝 | 화면 | kind | 누른 것 | 까닭 |
|---|---|---|---|---|
| 01c.png → 02.png | s01 → s02 | skipped | 이체 | 사이 상태가 캡처에 없다 (skipped) - 짐작으로 잇지 않는다 |
| 06c.png → 07.png | s06 → s07 | skipped | 은행 | 사이 상태가 캡처에 없다 (skipped) - 짐작으로 잇지 않는다 |
| 09a.png → 09b.png | s10 → s11 | skipped | - | 사이 상태가 캡처에 없다 (skipped) - 짐작으로 잇지 않는다 |
| 09b.png → 10.png | s11 → s12 | unknown | - | 누른 것을 모른다 (unknown) |

## s01 에서 닿지 않는 화면

s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13

## flow.json 에서 비운 칸

| 칸 | 까닭 |
|---|---|
| truth | 정답 값 (은행 · 계좌번호 · 금액 · 틀린 값) - 스크린샷에 '정답' 은 없다 |
| required_ids | 꼭 있어야 할 DOM id - 규칙 마크업에는 id 를 짓지 않았다 (요소는 data-src · data-action) |
| expect | 화면마다 확인할 값 - 정답 값이 없어 비움 |
| done_amount | 완료 화면의 금액 선택자 - 정답 값이 없어 넣지 않음 |
| error_paths[].about · condition · uses · notice_any · inputs | 오류 조건 · 입력 - 스크린샷에 보이지 않는다 (만들지 않는다) |
| steps (s01 다음) | s01 → s02 짝이 skipped 라 이동이 없다 - 과제 길이 s01 에서 끊긴다 |

## 찍지 않은 상태로 보이는 것 (skipped 짝)

01c.png → 02.png, 06c.png → 07.png, 09a.png → 09b.png

## 검출 · 의미 층 쪽

- 의미 층 경고 (칸 짝 검사): 없음

- 검출 놓침은 만드는 줄에서는 알 수 없다 (정답과 견주는 것은 채점 쪽 - list_compare.py).
- 오류 경로의 recover 는 오류 화면의 첫 누를 것, back_to 는 그 짝의 앞 화면이다 - 실제로 어느 화면에서 오류가 났는지는 스크린샷에 없다.

