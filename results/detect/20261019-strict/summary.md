# 스크린샷만 (--inputs strict) 실행 견주기 (2026-10-19)

만드는 줄의 입력은 캡처 PNG(파일 이름 순)뿐 - 이름표 · 이어 붙이기 묶음 · 과제 이름 · 로고 규칙(LOGO_HEAD) 없이. 채점(정답지 · 이름표로 짝짓기)은 옛 판과 같다. 검출(OmniParser · OCR)은 D2.5 final 그대로이고 로고 규칙 이름만 지웠다 (`detect/_strict.json`).

## 1. 이어 붙이기 자동 판정

stitch.GROUPS (연구자): 01a+01b+01c · 05a+05b+05c · 06a+06b+06c

| 설정 | 기준 | 나온 묶음 | GROUPS 와 같나 |
|---|---|---|---|
| A | {"text_min": 1, "boxes_min": 1, "pixels": true, "min_shift": 1} | 01a+01b+01c · 02+03 · 04+05a+05b+05c+06a+06b+06c+07 | 다름 |
| B | {"text_min": 2, "boxes_min": 1, "pixels": false, "min_shift": 100} | 01a+01b+01c · 05a+05b+05c · 06a+06b+06c | 같음 |
| C | {"text_min": 1, "boxes_min": 1, "pixels": true, "min_shift": 100} | 01a+01b+01c · 05a+05b+05c · 06a+06b+06c+07 | 다름 |

이웃 짝마다 (설정 B - 기본):

| 짝 | 같은 화면 | 어긋남 | 방법 | 근거 수 |
|---|---|---|---|---|
| 01a → 01b | 예 | 1759 | boxes | 1 |
| 01b → 01c | 예 | 473 | text | 13 |
| 01c → 02 | - | - | - | - |
| 02 → 03 | - | - | - | - |
| 03 → 04 | - | - | - | - |
| 04 → 05a | - | - | - | - |
| 05a → 05b | 예 | 1194 | boxes | 3 |
| 05b → 05c | 예 | 1195 | text | 3 |
| 05c → 06a | - | - | - | - |
| 06a → 06b | 예 | 1319 | boxes | 3 |
| 06b → 06c | 예 | 224 | text | 12 |
| 06c → 07 | - | - | - | - |
| 07 → 07a | - | - | - | - |
| 07a → 08 | - | - | - | - |
| 08 → 09a | - | - | - | - |
| 09a → 09b | - | - | - | - |
| 09b → 10 | - | - | - | - |
| 10 → 11 | - | - | - | - |

## 2. 흐름 D4 - 이름표 있음 (20261013-d4) 대 없음 (strict)

의미 층 역할은 둘 다 20261013-d3b (이름표 효과만 보려고 같게 둔다 - 그 역할은 과제 이름 · 단위 이름이 든 v1 프롬프트로 만든 것이다).

| 짝 | 전 (이름표 있음) | 후 (이름표 없음) | 정답 |
|---|---|---|---|
| 01a → 01b | - · scroll | - · scroll | - · scroll |
| 01b → 01c | - · scroll | - · scroll | - · scroll |
| 01c → 02 | 이체 · skipped ✗ | 이체 · tap | 이체 · tap |
| 02 → 03 | 계좌번호 직접 · tap | 계좌번호 직접 · tap | 계좌번호 직접 입력 · tap |
| 03 → 04 | 계좌번호 \|없이 숫자만 입력 · tap | 계좌번호 \|없이 숫자만 입력 · tap | 계좌번호 · tap |
| 04 → 05a | 은행 또는 증권사 선택 · tap | 은행 또는 증권사 선택 · tap | 은행 또는 증권사 선택 ⌄ · tap |
| 05a → 05b | - · scroll | - · scroll | - · scroll |
| 05b → 05c | - · scroll | - · scroll | - · scroll |
| 05c → 06a | 증권사 · tap | 증권사 · tap | 증권사 · tap |
| 06a → 06b | - · scroll | - · scroll | - · scroll |
| 06b → 06c | - · scroll | - · scroll | - · scroll |
| 06c → 07 | - · skipped ✗ | - · skipped ✗ | 은행 · skipped |
| 07 → 07a | +1만 · tap ✗ | +1만 · tap ✗ | 숫자 키 · skipped |
| 07a → 08 | 다음 · tap | 다음 · tap | 다음 · tap |
| 08 → 09a | 보내기 · tap | 보내기 · tap | 보내기 · tap |
| 09a → 09b | - · unknown ✗ | - · skipped ✗ | 숫자 키 · skipped |
| 09b → 10 | - · skipped ✗ | - · skipped ✗ | 숫자 키 · tap |
| 10 → 11 | - · error_path | 상세보기 · tap ✗ | - · error_path |

| | 전 | 후 |
|---|---|---|
| 누른 것 맞음 | 14/18 | 13/18 |
| kind 맞음 | 14/18 | 15/18 |
| 둘 다 맞음 | 13/18 | 13/18 |


## 3. 의미 층 - v1 + 로고 규칙 (20261013-d3b) 대 v2 strict (홈 · 은행)

그림 이름 = 정답 aria-label (닿은 요소의 image_name · icon.name 가운데 같은 글이 있으면 맞음. 전은 로고 규칙의 고정 이름 포함):

|  | 전 (로고 규칙 + v1) | 후 (strict v2) |
|---|---|---|
| 홈 전체 | 11/19 | 15/19 |
| 은행 - 은행 로고 | 37/38 | 30/38 |
| 은행 - 그 밖 | 0/0 | 0/0 |
| 은행 전체 | 37/38 | 30/38 |

### 바뀐 요소 (kind 가 바뀌었거나 icon · text_is_icon · text_fixed 가 찬 것)

| 단위 | id | 원래 text | kind (전 → 후) | icon | text_is_icon | text_fixed |
|---|---|---|---|---|---|---|
| 홈 | 01a:b5 | - | system → system | 이동통신 신호 아이콘 | - | - |
| 홈 | 01a:b7 | - | system → system | 와이파이 아이콘 | - | - |
| 홈 | 01a:b2 | - | button → button | 웃는 말풍선 아이콘 | - | - |
| 홈 | 01a:b1 | - | button → button | 지갑 아이콘 | - | - |
| 홈 | 01a:b0 | - | button → button | 알림 아이콘 | - | - |
| 홈 | 01a:b3 | - | button → button | 검색 아이콘 | - | - |
| 홈 | 01a:b8 | 홍길동님 C | link → link | C 로고 | - | - |
| 홈 | 01a:b21 | - | button → button | 자산 아이콘 | - | - |
| 홈 | 01a:b13 | 절세혜택과 안정적인 노후,IRP로 준비하세요 | link → button | - | - | - |
| 홈 | 01a:t11 | Pick E체크캐릭터형(하리보) | text → text | - | - | Pick E 체크캐릭터형(하리보) |
| 홈 | 01a:b20 | 팽겨요 | link → link | 땡겨요 아이콘 | - | 땡겨요 |
| 홈 | 01a:t14 | 팽겨요 | text → text | - | - | 땡겨요 |
| 홈 | 01a:b4 | 7월 소비 C | link → link | 7월 소비 아이콘 | - | - |
| 홈 | 01a:b22 | - | button → button | 7월 소비 아이콘 | - | - |
| 홈 | 01a:t22 | C | button → button | 7월 소비 아이콘 | 예 | - |
| 홈 | 01b:b16 | 오늘쓴 돈 0원 | link → link | 오늘 쓴 돈 아이콘 | - | 오늘 쓴 돈 0원 |
| 홈 | 01b:t0 | 오늘쓴 돈 | text → text | - | - | 오늘 쓴 돈 |
| 홈 | 01b:b2 | 쓸때마다 쌓이고,현금처럼 쓰는 카드 P 마이 | text → text | 마이신한포인트 아이콘 | - | - |
| 홈 | 01b:t4 | P | text → image | 마이신한포인트 아이콘 | - | - |
| 홈 | 01c:b6 | 추천서비스 | link → link | 추천서비스 아이콘 | - | - |
| 홈 | 01b:t8 | > | image → image | 추천서비스 아이콘 | 예 | - |
| 홈 | 01c:b1 | SOL패밀리 가족과 함께하는 금융생활 | link → link | SOL패밀리 아이콘 | - | - |
| 홈 | 01c:b0 | 급여클럽+ 푸 급여이체 우대 혜택 | link → link | 급여클럽+ 아이콘 | - | 급여클럽+ 급여이체 우대 혜택 |
| 홈 | 01c:t4 | 푸 | button → button | 급여클럽+ 아이콘 | 예 | - |
| 홈 | 01c:b3 | 내 카드 승인내역 푸 모든 카드 실시간 승인 | link → link | 내 카드 승인내역 아이콘 | - | 내 카드 승인내역 모든 카드 실시간 승인내역 |
| 홈 | 01b:t15 | 푸 | button → button | 내 카드 승인내역 아이콘 | 예 | - |
| 홈 | 01b:b12 | 더 많은 금융자산 모두 연결하면 커피쿠폰 즉 | link → link | 꽃 아이콘 | - | 더 많은 금융자산 모두 연결하면 커피쿠폰 즉시지급! 이벤트 바로가기 |
| 홈 | 01c:b14 | 이벤트 바로가기 ^ | link → link | 이벤트 바로가기 아이콘 | - | 이벤트 바로가기 |
| 홈 | 01b:t20 | ^ | image → image | 이벤트 바로가기 아이콘 | 예 | - |
| 홈 | 01b:b17 | 신한카드 나에게 맞는 카드 찾기 | link → link | 신한카드 아이콘 | - | - |
| 홈 | 01c:b18 | - | button → button | 신한카드 아이콘 | - | - |
| 홈 | 01c:b2 | 신한투자증권 지금 뜨는 주식 보러가기 | link → link | 신한투자증권 아이콘 | - | - |
| 홈 | 01c:b19 | - | button → button | 신한투자증권 아이콘 | - | - |
| 홈 | 01c:b7 | 신한라이프 내게 필요한 보험,보장분석으로 확 | link → link | 신한라이프 아이콘 | - | - |
| 홈 | 01c:b20 | - | button → button | 신한라이프 아이콘 | - | - |
| 홈 | 01c:b10 | 혜택 | tab → tab | 혜택 아이콘 | - | - |
| 홈 | 01c:b8 | 상품 | tab → tab | 상품 아이콘 | - | - |
| 홈 | 01c:b9 | 금융 | tab → tab | 금융 아이콘 | - | - |
| 홈 | 01c:b12 | 주식 | tab → tab | 주식 아이콘 | - | - |
| 홈 | 01c:b11 | 홈 | tab → tab | 홈 아이콘 | - | - |
| 은행 | 05a:b18 | - | system → system | 통신 신호 아이콘 | - | - |
| 은행 | 05a:b19 | - | system → system | 와이파이 아이콘 | - | - |
| 은행 | 05a:b22 | - | system → system | 뒤로 및 닫기 아이콘 | - | - |
| 은행 | 05a:b23 | - | system → system | 닫기 아이콘 | - | - |
| 은행 | 05a:b21 | < | system → system | 뒤로 아이콘 | 예 | - |
| 은행 | 05a:t2 | < | system → system | 뒤로 아이콘 | 예 | - |
| 은행 | 05a:b20 | - | system → system | 닫기 아이콘 | - | - |
| 은행 | 05a:b17 | - | back_close → back_close | 닫기 아이콘 | - | - |
| 은행 | 05a:b11 | 신한 | choice → choice | 신한 로고 | - | - |
| 은행 | 05a:b9 | 제주 | choice → choice | 제주 로고 | - | - |
| 은행 | 05a:b10 | 국민 | choice → choice | 국민 로고 | - | - |
| 은행 | 05a:b8 | 기업 | choice → choice | 기업 로고 | - | - |
| 은행 | 05a:b5 | NH 농협 | choice → choice | 농협 로고 | - | - |
| 은행 | 05a:b3 | 산업 | choice → choice | 산업 로고 | - | - |
| 은행 | 05a:t10 | NH | text → image | 농협 로고 | - | - |
| 은행 | 05a:b0 | 신협 | choice → choice | 신협 로고 | - | - |
| 은행 | 05a:b7 | Sh 수협 | choice → choice | 수협 로고 | - | - |
| 은행 | 05a:b4 | 우리 | choice → choice | 우리 로고 | - | - |
| 은행 | 05a:t14 | Sh | text → image | 수협 로고 | - | - |
| 은행 | 05a:b6 | 하나 | choice → choice | 하나 로고 | - | - |
| 은행 | 05a:b1 | citi 한국씨티 | choice → choice | 한국씨티 로고 | - | - |
| 은행 | 05a:b2 | D 카카오뱅크 | choice → choice | 카카오뱅크 로고 | - | 카카오뱅크 |
| 은행 | 05a:t18 | D | text → image | 카카오뱅크 로고 | 예 | - |
| 은행 | 05a:t19 | citi | text → image | 한국씨티 로고 | - | - |
| 은행 | 05b:b11 | BiNV 경남 | choice → choice | 경남 로고 | - | BNK 경남 |
| 은행 | 05b:b9 | 토스뱅크 | choice → choice | 토스뱅크 로고 | - | - |
| 은행 | 05b:b10 | Kbank 케이뱅크 | choice → choice | 케이뱅크 로고 | - | - |
| 은행 | 05b:t8 | BiNV | text → image | 경남 로고 | - | BNK |
| 은행 | 05a:t24 | BNV | text → image | 경남 로고 | - | BNK |
| 은행 | 05b:t7 | Kbank | text → image | 케이뱅크 로고 | - | - |
| 은행 | 05b:b6 | BNV 부산 | choice → choice | 부산 로고 | - | BNK 부산 |
| 은행 | 05b:b8 | 광주 | choice → choice | 광주 로고 | - | - |
| 은행 | 05b:b5 | 아이엠뱅크(대. | choice → choice | 아이엠뱅크(대... 로고 | - | 아이엠뱅크(대... |
| 은행 | 05b:t12 | BNV | text → image | 부산 로고 | - | BNK |
| 은행 | 05b:t14 | 아이엠뱅크(대. | text → text | - | - | 아이엠뱅크(대... |
| 은행 | 05b:b3 | 전북 | choice → choice | 전북 로고 | - | - |
| 은행 | 05b:b0 | 회원수협 | choice → choice | 회원수협 로고 | - | - |
| 은행 | 05b:b1 | 새마을 | choice → choice | 새마을 로고 | - | - |
| 은행 | 05b:b2 | SB 저축은행 | choice → choice | 저축은행 로고 | - | - |
| 은행 | 05b:b4 | 지역농.축협 | choice → choice | 지역농.축협 로고 | - | - |
| 은행 | 05b:b7 | 우체국 | choice → choice | 우체국 로고 | - | - |
| 은행 | 05b:t19 | SB | text → image | 저축은행 로고 | - | - |
| 은행 | 05b:b13 | 중국건설 | choice → choice | 중국건설 로고 | - | - |
| 은행 | 05b:b14 | 도이치 | choice → choice | 도이치 로고 | - | - |
| 은행 | 05b:b12 | 중국 | choice → choice | 중국 로고 | - | - |
| 은행 | 05c:b6 | BNP파리바 | choice → choice | BNP파리바 로고 | - | - |
| 은행 | 05c:b7 | BOA | choice → choice | BOA 로고 | - | - |
| 은행 | 05c:b8 | 중국공상 | choice → choice | 중국공상 로고 | - | - |
| 은행 | 05c:b2 | SC | choice → choice | SC 로고 | - | - |
| 은행 | 05c:b3 | HSBC | choice → choice | HSBC 로고 | - | - |
| 은행 | 05c:b0 | JP모간 | choice → choice | JP모간 로고 | - | - |
| 은행 | 05c:b4 | 산림조합 | choice → choice | 산림조합 로고 | - | - |
| 은행 | 05c:b5 | 지방세 | choice → choice | 지방세 아이콘 | - | - |
| 은행 | 05c:b1 | 국세 | choice → choice | 국세 아이콘 | - | - |
| 은행 | 05c:b9 | 국고금 | choice → choice | 국고금 아이콘 | - | - |
| 은행 | 05c:b10 | 관세 | choice → choice | 관세 아이콘 | - | - |

## 4. 유료 호출 (gpt-6.1-sol)

| 무엇 | 호출 | 입력 토큰 | 출력 토큰 | 실제 USD | 어림 USD (생각 = 답) |
|---|---|---|---|---|---|
| 의미 층 v2 (홈 · 은행) | 2 | 35600 | 20070 | 0.2719 | 0.4031 |
| 흐름 D4 strict (18쌍, 글만) | 1 | 7053 | 1062 | 0.0247 | 0.0429 |
| LLM 시안 strict (홈) | 1 | 13620 | 9238 | 0.1196 | 0.1664 |
| 합계 | 4 |  |  | 0.4162 |  |
