# 흐름 추정 시험 D4 (flow)

캡처 순서와 이름표(`None`), 요소(`results/detect/20261019-strict2/detect`)와 의미 층 역할(`results/detect/20261019-strict2/semantic`)로 모델(`gpt-6.1-sol`, reasoning medium)이 캡처 짝마다 누른 것을 추정했다. 보낸 것: 글 + 그림 36 (짝마다 앞 · 뒤 캡처, 폭 390) - 캡처 목록 · 단위마다 누를 수 있는 요소 · 짝 목록. 프롬프트 `tools/screen_detect/FLOW_PROMPT_STRICT.md` (2cdee2fae356). 상태 ok · 시도 2 · 쓴 돈 $0.1117.

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
| 01a → 01b | home → home | - | scroll | 0.99 | - | scroll · 같은 상태 | 맞음 | 맞음 | 홈 화면을 아래로 스크롤해 소비 및 추천서비스 영역이 나타났다. |
| 01b → 01c | home → home | - | scroll | 0.99 | - | scroll · 같은 상태 | 맞음 | 맞음 | 같은 홈 화면에서 더 아래의 금융그룹 및 홈 설정 영역으로 이동했다. |
| 01c → 02 | home → recipient | 이체 (01a:b18) | skipped | 0.90 | 이체 (go-recipient) | tap · 누름 1번 | 맞음 | **틀림** | 위로 스크롤해 이체 버튼을 누른 것으로 보이며, 그 중간 화면은 캡처되지 않았다. |
| 02 → 03 | recipient → account | 계좌번호 직접 (t7) | tap | 0.98 | 계좌번호 직접 입력 (go-account) | tap · 누름 1번 | 맞음 | 맞음 | 계좌번호 직접 입력 영역을 눌러 받는 계좌 입력 화면으로 이동했다. |
| 03 → 04 | account → account#2 | 계좌번호 \|없이 숫자만 입력 (b1) | tap | 0.96 | 계좌번호 (acc-field) | tap · 누름 1번 | 맞음 | 맞음 | 계좌번호 입력란을 눌러 숫자판이 열렸다. |
| 04 → 05a | account#2 → bank | 은행 또는 증권사 선택 (b0) | tap | 0.99 | 은행 또는 증권사 선택 ⌄ (open-bank) | tap · 누름 1번 | 맞음 | 맞음 | 금융기관 선택란을 눌러 은행 목록이 열렸다. |
| 05a → 05b | bank → bank | - | scroll | 0.99 | - | scroll · 같은 상태 | 맞음 | 맞음 | 은행 선택 목록을 아래로 스크롤했다. |
| 05b → 05c | bank → bank | - | scroll | 0.99 | - | scroll · 같은 상태 | 맞음 | 맞음 | 같은 은행 목록의 하단으로 스크롤했다. |
| 05c → 06a | bank → bank+tab-sec | - | unknown | 0.99 | 증권사 (tab-sec) | tap · 누름 1번 | **틀림** | **틀림** | 증권사 탭을 누른 전환으로 보이지만 앞 단위의 요소 목록이 비어 있어 해당 id를 지정할 수 없다. |
| 06a → 06b | bank+tab-sec → bank+tab-sec | - | scroll | 0.99 | - | scroll · 같은 상태 | 맞음 | 맞음 | 증권사 선택 목록을 아래로 스크롤했다. |
| 06b → 06c | bank+tab-sec → bank+tab-sec | - | scroll | 0.99 | - | scroll · 같은 상태 | 맞음 | 맞음 | 같은 증권사 목록을 더 내려 마지막 항목들이 나타났다. |
| 06c → 07 | bank+tab-sec → amount | 은행 (06a:b16) | skipped | 0.80 | 은행 (tab-bank) | skipped · 누름 15번 · 사이 상태 bank, amount~1, amount~2 | 맞음 | 맞음 | 뒤 화면의 받는 계좌가 신한이므로 은행 탭으로 돌아가 계좌 선택·입력을 진행한 중간 상태가 생략된 것으로 보인다. |
| 07 → 07a | amount → confirm~1 | +1만 (b1) | tap | 0.98 | 숫자 키 (값 넣기) | skipped · 누름 5번 | **틀림** | **틀림** | 금액이 비어 있던 상태에서 10,000원으로 바뀌었다. |
| 07a → 08 | confirm~1 → confirm | 다음 (b15) | tap | 0.99 | 다음 (amount-next) | tap · 누름 1번 | 맞음 | 맞음 | 입력한 10,000원의 이체 확인 화면으로 이동했다. |
| 08 → 09a | confirm → password | 보내기 (t15) | tap | 0.99 | 보내기 (send) | tap · 누름 1번 | 맞음 | 맞음 | 보내기를 눌러 계좌 비밀번호 입력 화면이 열렸다. |
| 09a → 09b | password → password | - | skipped | 0.99 | 숫자 키 | skipped · 누름 3번 | **틀림** | 맞음 | 비밀번호 세 자리를 입력한 상태로 바뀌어 중간 입력 상태가 생략되었으며 첫 숫자는 알 수 없다. |
| 09b → 10 | password → done | - | unknown | 0.98 | 숫자 키 | tap · 누름 1번 | **틀림** | **틀림** | 마지막 비밀번호 숫자를 눌러 이체가 완료된 것으로 보이지만 어떤 숫자인지는 알 수 없다. |
| 10 → 11 | done → error:wrong-account | - | error_path | 0.99 | - | error_path · 오류 경로 error:wrong-account (갈라지는 상태 bank) | 맞음 | 맞음 | 뒤 화면은 계좌번호 100의 오류 안내이며, 앞 완료 화면에는 이 오류를 직접 낸 입력 요소가 없다. |

## 토큰 · 비용

| 시도 | 입력 토큰 | 출력 토큰 (생각) | 비용 USD | 문제 |
|---|---|---|---|---|
| 1 | 22134 | 1140 (126) | 0.0557 | 05c.png -> 06a.png: kind 가 tap 인데 tap 이 null 이다; 09b.png -> 10.png: kind 가 tap 인데 tap 이 null 이다 |
| 2 | 22194 | 1163 (137) | 0.0560 | - |
