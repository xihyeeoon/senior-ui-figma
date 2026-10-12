# 이름 대응표 근거 (`renames.json`)

상태: 잠정 — 2026-10-12 연구자가 figma 채팅의 제안 (원본 HTML 근거) 을 받아들임. 더미앱으로 확인하기 전이며 나중에 고칠 수 있다. 고칠 때는 renames.json 과 이 파일을 함께 고치고 npm run build 뒤 Figma 에서 다시 그린다.

형식과 표시 규칙은 `RULES.md` 4.6. 줄 번호는 `inputs/original_transfer.html` (2026-10-12 에 열어 확인).
화면 키는 `sheet.screen` 값이다: 받는 사람 고르기 `recipient` · 계좌 3장 (받는 계좌 입력 · 입력한 계좌 확인 ·
계좌번호 오류 수정) `account` · 은행 3장 (받는 은행 고르기 · 받는 은행 다시 고르기 · 받는 은행 목록) `bank` ·
보낼 금액 입력 `amount` · 이체 내용 확인 `confirm` · 이체 비밀번호 입력 `password`.

## run `20261008-131136`

| 생성 action | 대응 | 근거 |
|---|---|---|
| `settings-toggle` | `new` | 원본은 펼치기 없이 쉬운홈 · 홈화면 설정 · 금액 숨기기를 바로 보인다, 300줄 |
| `service` | `made-pressable` | 원본 SOL패밀리 · 급여클럽+ · 내 카드 승인내역 · 신한카드 · 신한투자증권 · 신한라이프는 data-action 없는 div.svc, 283–285 · 295–297줄 |
| `previous` | `recipient` → `back-home` · `account` → `back-recipient` · `amount` → `back-account` · `confirm` → `back-amount` · `password` → `new` | 원본 ‹ 아이콘 315 · 351 · 373 · 391줄. 비밀번호 화면엔 ✕ back-home 만 있고 ‹ 없음, 411줄 |
| `cancel` | `account` → `close-account` · `bank` → `close-bank` · `amount` → `back-home` · `confirm` → `back-home` · `password` → `back-home` · `recipient` → `new` | 원본 ✕ 아이콘 351 · 337 · 373 · 391 · 411줄. 받는 사람 화면엔 ‹ 뿐 |
| `frequent-edit` | `made-pressable` | 원본 "편집" 은 oos-frequent 줄 안의 span.tag, 324줄 |
| `acc-clear` | `acc-clear` | 원본 358줄 같은 이름, 계좌번호를 넣었을 때만 보임 |
| `acc-fix` | `close-error` | 원본 오류 창 닫기 433 · 437줄 |
| `amt-clear` | `new` | 원본은 한 자리 지우기 del 뿐, 527줄 |
| `edit-account` | `new` | 원본 "받는 계좌" 는 data-action 없는 글, 400줄. 확인 → 계좌로 바로 가는 길 없음 |
| `edit-amount` | `back-amount` | 원본 확인 화면 ‹ 가 금액 화면으로, 391줄 |
| `edit-memo-to` | `made-pressable` | 원본 "받는분 메모 김철수 ✎" data-action 없음, 401줄 |
| `edit-memo-own` | `made-pressable` | 원본 "내통장 메모 김철수 ✎" data-action 없음, 402줄 |
| `pw-send` | `new` | 원본은 4자리 입력 즉시 완료로 감, 672–674줄 |

`acc-clear` · `close-error` 는 원본 HTML 에 있지만 원본을 걷는 동안 보이지 않아 `original.where` 에 없다.
그래서 그릴 때 "대응표 확인" 줄이 두 개 나온다 (RULES.md 4.6).
