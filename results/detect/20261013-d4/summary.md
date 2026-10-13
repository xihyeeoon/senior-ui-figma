# 흐름 추정 시험 D4 (20261013-d4)

캡처 순서와 이름표(`origin/feat/see-captures:inputs/captures/transfer/captures.json`), 요소(`results/detect/20261013-d25/final`)와 의미 층 역할(`results/detect/20261013-d3b`)로 모델(`gpt-6.1-sol`, reasoning medium)이 캡처 짝마다 누른 것을 추정했다. 보낸 것: 글만 (그림 0) - 캡처 목록 · 단위마다 누를 수 있는 요소 · 짝 목록. 프롬프트 `tools/screen_detect/FLOW_PROMPT.md` (03856f328df9). 상태 ok · 시도 1 · 쓴 돈 $0.0258.

정답: 원본 재현 HTML 을 원본 흐름대로 걸은 timeline (`truth.json`). 이름표 → 상태, 짝 사이에 실제로 누른 것 (compare_flow.py 머리말).

## 합계

| 항목 | 값 |
|---|---|
| 누른 것 맞음 | 14/18 |
| kind 맞음 | 14/18 |
| 둘 다 맞음 | 13/18 |
| confidence < 0.8 에서 틀린 짝 | 0/0 |
| confidence ≥ 0.8 에서 틀린 짝 | 5/18 |

| confidence | 짝 | 틀린 짝 |
|---|---|---|
| 0.0~0.5 | 0 | 0 |
| 0.5~0.8 | 0 | 0 |
| 0.8~1.0 | 18 | 5 |

## 짝마다 (연구자 검토용)

| 짝 | 상태 | 추정: 누른 것 (글) | kind | conf | 정답: 누른 것 | 정답 kind | 누른 것 | kind | 근거 |
|---|---|---|---|---|---|---|---|---|---|
| 01a → 01b | home → home | - | scroll | 1.00 | - | scroll · 같은 상태 | 맞음 | 맞음 | 홈 화면을 아래로 스크롤한 캡처다. |
| 01b → 01c | home → home | - | scroll | 1.00 | - | scroll · 같은 상태 | 맞음 | 맞음 | 같은 홈 화면의 맨 아래로 스크롤했다. |
| 01c → 02 | home → recipient | 이체 (01a:b18) | skipped | 0.86 | 이체 (go-recipient) | tap · 누름 1번 | 맞음 | **틀림** | 홈 상단의 이체로 진입한 것으로 보이며, 상단으로 돌아간 상태는 캡처되지 않았다. |
| 02 → 03 | recipient → account | 계좌번호 직접 (t7) | tap | 0.94 | 계좌번호 직접 입력 (go-account) | tap · 누름 1번 | 맞음 | 맞음 | 계좌번호 직접 입력을 눌러 계좌 입력 화면으로 이동했다. |
| 03 → 04 | account → account#2 | 계좌번호 \|없이 숫자만 입력 (b1) | tap | 1.00 | 계좌번호 (acc-field) | tap · 누름 1번 | 맞음 | 맞음 | 계좌번호 입력란을 눌러 숫자 키패드를 열었다. |
| 04 → 05a | account#2 → bank | 은행 또는 증권사 선택 (b0) | tap | 0.98 | 은행 또는 증권사 선택 ⌄ (open-bank) | tap · 누름 1번 | 맞음 | 맞음 | 기관 선택 버튼을 눌러 은행 목록을 열었다. |
| 05a → 05b | bank → bank | - | scroll | 1.00 | - | scroll · 같은 상태 | 맞음 | 맞음 | 같은 은행 목록을 아래로 스크롤했다. |
| 05b → 05c | bank → bank | - | scroll | 1.00 | - | scroll · 같은 상태 | 맞음 | 맞음 | 은행 목록의 맨 아래로 스크롤했다. |
| 05c → 06a | bank → bank+tab-sec | 증권사 (05a:b16) | tap | 0.98 | 증권사 (tab-sec) | tap · 누름 1번 | 맞음 | 맞음 | 기관 유형을 증권사 탭으로 전환했다. |
| 06a → 06b | bank+tab-sec → bank+tab-sec | - | scroll | 1.00 | - | scroll · 같은 상태 | 맞음 | 맞음 | 같은 증권사 목록을 아래로 스크롤했다. |
| 06b → 06c | bank+tab-sec → bank+tab-sec | - | scroll | 1.00 | - | scroll · 같은 상태 | 맞음 | 맞음 | 증권사 목록의 맨 아래로 스크롤했다. |
| 06c → 07 | bank+tab-sec → amount | - | skipped | 0.93 | 은행 (tab-bank) | skipped · 누름 15번 · 사이 상태 bank, amount~1, amount~2 | **틀림** | 맞음 | 기관 선택과 계좌 입력 완료 과정이 생략된 것으로 보이나, 처음 누른 기관은 알 수 없다. |
| 07 → 07a | amount → confirm~1 | +1만 (b1) | tap | 0.95 | 숫자 키 (값 넣기) | skipped · 누름 5번 | **틀림** | **틀림** | +1만 버튼으로 10,000원을 입력한 것으로 보인다. |
| 07a → 08 | confirm~1 → confirm | 다음 (b15) | tap | 0.99 | 다음 (amount-next) | tap · 누름 1번 | 맞음 | 맞음 | 금액 입력 후 다음을 눌러 이체 확인 화면으로 이동했다. |
| 08 → 09a | confirm → password | 보내기 (t15) | tap | 0.99 | 보내기 (send) | tap · 누름 1번 | 맞음 | 맞음 | 보내기를 눌러 비밀번호 입력 화면을 열었다. |
| 09a → 09b | password → password | - | unknown | 0.98 | 숫자 키 | skipped · 누름 3번 | **틀림** | **틀림** | 비밀번호 숫자를 입력했지만 어떤 숫자를 몇 번 눌렀는지는 알 수 없다. |
| 09b → 10 | password → done | - | skipped | 0.85 | 숫자 키 | tap · 누름 1번 | **틀림** | **틀림** | 남은 비밀번호 입력과 인증 완료 과정이 생략된 것으로 보이며, 첫 입력 숫자는 알 수 없다. |
| 10 → 11 | done → error:wrong-account | - | error_path | 1.00 | - | error_path · 오류 경로 error:wrong-account (갈라지는 상태 bank) | 맞음 | 맞음 | 뒤 캡처는 잘못된 계좌번호로 생긴 오류이며, 완료 화면에는 해당 오류를 낸 입력 요소가 없다. |

## 토큰 · 비용

| 시도 | 입력 토큰 | 출력 토큰 (생각) | 비용 USD | 문제 |
|---|---|---|---|---|
| 1 | 7445 | 1088 (119) | 0.0258 | - |
