# 목록 대조 - 옛 원본 대 새 원본 (results/detect/20261019-assembly3/rule)

옛: `results/detect/20261013-d3b/truth.json` (옛 원본을 옛 흐름대로 걸은 목록) + `git show origin/feat/db-principles:flows/original.json`. 새: `original.html` · `flow.json`. 화면 짝은 글이 가장 많이 찾아지는 것 (찾은 비율 0.3 이상).

## 화면 짝 (옛 상태 15 · 새 화면 13)

| 옛 상태 | 캡처 있음 | 새 화면 | 찾은 비율 |
|---|---|---|---|
| home | 예 | s01 | 0.94 |
| recipient | 예 | s02 | 0.8 |
| account | 예 | s03 | 0.71 |
| account#2 | 예 | s04 | 0.88 |
| bank | 예 | s05 | 0.95 |
| bank+tab-sec | 예 | s06 | 0.94 |
| amount~1 | 아니오 | s04 | 0.82 |
| amount~2 | 아니오 | s04 | 0.76 |
| amount | 예 | s07 | 0.91 |
| confirm~1 | 예 | s07 | 0.87 |
| confirm | 예 | s09 | 0.85 |
| password | 예 | s10 | 0.86 |
| done | 예 | s12 | 0.75 |
| error:wrong-account | 예 | s13 | 0.57 |
| error:wrong-bank | 아니오 | - | 0.17 |

## 항목별

| 항목 | 같음 | 다름 | 새에만 | 옛에만 | 캡처 없음 |
|---|---|---|---|---|---|
| 선택지 값 | 98 | 0 | 31 | 4 | 0 |
| 그림 자리 이름 | 81 | 0 | 49 | 9 | 0 |
| 과제 밖 입구 | 25 | 0 | 70 | 6 | 0 |
| 입력칸 | 2 | 1 | 6 | 3 | 0 |
| 오류 경로 | 1 | 0 | 0 | 0 | 1 |
| 과제 길 | 8 | 0 | 0 | 0 | 0 |

## 다름 · 옛에만 · 새에만 · 캡처 없음 상세


### 선택지 값

| 나눔 | 화면 | 무엇 |
|---|---|---|
| 새에만 | s04 ↔ account#2 · amount~1 · amount~2 | 삭제 아이콘 |
| 새에만 | s06 ↔ bank+tab-sec | 06a:b14 |
| 새에만 | s06 ↔ bank+tab-sec | pay |
| 새에만 | s06 ↔ bank+tab-sec | LS증권 |
| 옛에만 | s07 ↔ amount · confirm~1 | 50000 |
| 옛에만 | s07 ↔ amount · confirm~1 | 100000 |
| 옛에만 | s07 ↔ amount · confirm~1 | all |
| 옛에만 | s07 ↔ amount · confirm~1 | 00 |
| 새에만 | s07 ↔ amount · confirm~1 | 지우기 아이콘 |
| 새에만 | s08 ↔ - | 1 |
| 새에만 | s08 ↔ - | 3 |
| 새에만 | s08 ↔ - | 2 |
| 새에만 | s08 ↔ - | 4 |
| 새에만 | s08 ↔ - | 6 |
| 새에만 | s08 ↔ - | 5 |
| 새에만 | s08 ↔ - | 7 |
| 새에만 | s08 ↔ - | 9 |
| 새에만 | s08 ↔ - | 8 |
| 새에만 | s08 ↔ - | 지우기 아이콘 |
| 새에만 | s08 ↔ - | 00 |
| 새에만 | s08 ↔ - | 0 |
| 새에만 | s10 ↔ password | 재배열 |
| 새에만 | s10 ↔ password | 지우기 아이콘 |
| 새에만 | s11 ↔ - | 8 |
| 새에만 | s11 ↔ - | 6 |
| 새에만 | s11 ↔ - | 0 |
| 새에만 | s11 ↔ - | 2 |
| 새에만 | s11 ↔ - | 4 |
| 새에만 | s11 ↔ - | 1 |
| 새에만 | s11 ↔ - | 9 |
| 새에만 | s11 ↔ - | 3 |
| 새에만 | s11 ↔ - | 5 |
| 새에만 | s11 ↔ - | 7 |
| 새에만 | s11 ↔ - | 재배열 |
| 새에만 | s11 ↔ - | 지우기 아이콘 |

### 그림 자리 이름

| 나눔 | 화면 | 무엇 |
|---|---|---|
| 옛에만 | s01 ↔ home | 메시지 아이콘 |
| 옛에만 | s01 ↔ home | 전체메뉴 아이콘 |
| 옛에만 | s01 ↔ home | 체크카드 아이콘 |
| 옛에만 | s01 ↔ home | 땡겨요 쿠폰 아이콘 |
| 새에만 | s01 ↔ home | 할인쿠폰 드려요 아이콘 |
| 새에만 | s01 ↔ home | 마이신한포인트 아이콘 |
| 새에만 | s01 ↔ home | 고정 핀 아이콘 |
| 새에만 | s01 ↔ home | 고정 핀 아이콘 |
| 새에만 | s01 ↔ home | 웃는 말풍선 아이콘 |
| 새에만 | s01 ↔ home | 검색 아이콘 |
| 새에만 | s01 ↔ home | 홍길동님 아이콘 |
| 새에만 | s01 ↔ home | 새로고침 아이콘 |
| 새에만 | s01 ↔ home | 알 수 없는 아이콘 |
| 옛에만 | s02 ↔ recipient | 받는 사람 관리 아이콘 |
| 옛에만 | s02 ↔ recipient | 카메라 아이콘 |
| 새에만 | s02 ↔ recipient | 사람 추가 아이콘 |
| 새에만 | s02 ↔ recipient | 닫기 아이콘 |
| 새에만 | s02 ↔ recipient | 계좌번호 직접 입력 아이콘 |
| 새에만 | s03 ↔ account | 닫기 아이콘 |
| 새에만 | s04 ↔ account#2 · amount~1 · amount~2 | 닫기 아이콘 |
| 새에만 | s04 ↔ account#2 · amount~1 · amount~2 | 삭제 아이콘 |
| 옛에만 | s05 ↔ bank | 아이엠뱅크(대구) 로고 |
| 새에만 | s05 ↔ bank | 닫기 아이콘 |
| 새에만 | s05 ↔ bank | 농협 로고 |
| 새에만 | s05 ↔ bank | 농협 로고 |
| 새에만 | s05 ↔ bank | 한국씨티 로고 |
| 새에만 | s05 ↔ bank | 카카오뱅크 로고 |
| 새에만 | s05 ↔ bank | 경남 로고 |
| 새에만 | s05 ↔ bank | 경남 로고 |
| 새에만 | s05 ↔ bank | 경남 로고 |
| 새에만 | s05 ↔ bank | 케이뱅크 로고 |
| 새에만 | s05 ↔ bank | 부산 로고 |
| 새에만 | s05 ↔ bank | 부산 로고 |
| 새에만 | s05 ↔ bank | 아이엠뱅크(대... 로고 |
| 옛에만 | s06 ↔ bank+tab-sec | 유진투자증권 로고 |
| 새에만 | s06 ↔ bank+tab-sec | 닫기 아이콘 |
| 새에만 | s06 ↔ bank+tab-sec | 삼성증권 로고 |
| 새에만 | s06 ↔ bank+tab-sec | 유안타증권 로고 |
| 새에만 | s06 ↔ bank+tab-sec | 유안타증권 로고 |
| 새에만 | s06 ↔ bank+tab-sec | BNK투자증권 로고 |
| 새에만 | s06 ↔ bank+tab-sec | BNK투자증권 로고 |
| 새에만 | s07 ↔ amount · confirm~1 | 닫기 아이콘 |
| 새에만 | s07 ↔ amount · confirm~1 | 지우기 아이콘 |
| 새에만 | s08 ↔ - | 닫기 아이콘 |
| 새에만 | s08 ↔ - | 지우기 아이콘 |
| 옛에만 | s09 ↔ confirm | 신한 로고 |
| 새에만 | s09 ↔ confirm | 받는분 메모 아이콘 |
| 새에만 | s09 ↔ confirm | 내통장 메모 아이콘 |
| 새에만 | s09 ↔ confirm | 닫기 아이콘 |
| 새에만 | s10 ↔ password | 닫기 아이콘 |
| 새에만 | s10 ↔ password | 지우기 아이콘 |
| 새에만 | s11 ↔ - | 닫기 아이콘 |
| 새에만 | s11 ↔ - | 비밀번호 입력 표시 아이콘 |
| 새에만 | s11 ↔ - | 비밀번호 입력 표시 아이콘 |
| 새에만 | s11 ↔ - | 비밀번호 입력 표시 아이콘 |
| 새에만 | s11 ↔ - | 비밀번호 미입력 표시 아이콘 |
| 새에만 | s11 ↔ - | 지우기 아이콘 |
| 새에만 | s12 ↔ done | 이체 완료 아이콘 |

### 과제 밖 입구

| 나눔 | 화면 | 무엇 |
|---|---|---|
| 옛에만 | s01 ↔ home | 홈화면 설정 |
| 옛에만 | s01 ↔ home | 전체메뉴 |
| 옛에만 | s01 ↔ home | 메시지 |
| 옛에만 | s01 ↔ home | 포인트 |
| 옛에만 | s01 ↔ home | › |
| 새에만 | s01 ↔ home | › |
| 새에만 | s01 ↔ home | 땡겨요 |
| 새에만 | s01 ↔ home | 시작하기 |
| 새에만 | s01 ↔ home | a-s01-20 |
| 새에만 | s01 ↔ home | 추천서비스 › |
| 새에만 | s01 ↔ home | 고정 핀 아이콘 |
| 새에만 | s01 ↔ home | 내 카드 승인내역 모든 카드 실시간 승인내역 |
| 새에만 | s01 ↔ home | 고정 핀 아이콘 |
| 새에만 | s01 ↔ home | 신한카드 › 나에게 맞는 카드 찾기 |
| 새에만 | s01 ↔ home | 신한라이프 › 내게 필요한 보험, 보장분석으로 확인하기 |
| 새에만 | s01 ↔ home | 웃는 말풍선 아이콘 |
| 새에만 | s01 ↔ home | 검색 아이콘 |
| 새에만 | s01 ↔ home | 홍길동님 |
| 새에만 | s01 ↔ home | › 7월 소비 |
| 새에만 | s01 ↔ home | › |
| 새에만 | s01 ↔ home | 새로고침 아이콘 |
| 새에만 | s01 ↔ home | 오늘 쓴 돈 0원 |
| 새에만 | s01 ↔ home | 혜택 |
| 새에만 | s01 ↔ home | 금융 |
| 새에만 | s01 ↔ home | 주식 |
| 옛에만 | s02 ↔ recipient | 받는 사람 관리 |
| 새에만 | s02 ↔ recipient | 편집 |
| 새에만 | s02 ↔ recipient | ‹ |
| 새에만 | s02 ↔ recipient | 사람 추가 아이콘 |
| 새에만 | s02 ↔ recipient | 닫기 아이콘 |
| 새에만 | s02 ↔ recipient | 입력 |
| 새에만 | s02 ↔ recipient | 계좌번호 직접 입력 아이콘 |
| 새에만 | s03 ↔ account | 은행 또는 증권사 선택 |
| 새에만 | s03 ↔ account | 다음 |
| 새에만 | s03 ↔ account | ‹ ‹ |
| 새에만 | s03 ↔ account | ‹ |
| 새에만 | s03 ↔ account | 닫기 아이콘 |
| 새에만 | s04 ↔ account#2 · amount~1 · amount~2 | 계좌번호 없이 숫자만 입력 |
| 새에만 | s04 ↔ account#2 · amount~1 · amount~2 | 다음 |
| 새에만 | s04 ↔ account#2 · amount~1 · amount~2 | ‹ |
| 새에만 | s04 ↔ account#2 · amount~1 · amount~2 | ‹ |
| 새에만 | s04 ↔ account#2 · amount~1 · amount~2 | 닫기 아이콘 |
| 새에만 | s05 ↔ bank | 닫기 아이콘 |
| 새에만 | s05 ↔ bank | 은행 |
| 새에만 | s06 ↔ bank+tab-sec | 닫기 아이콘 |
| 새에만 | s06 ↔ bank+tab-sec | 증권사 |
| 새에만 | s06 ↔ bank+tab-sec | a-s06-04 |
| 새에만 | s06 ↔ bank+tab-sec | a-s06-05 |
| 새에만 | s07 ↔ amount · confirm~1 | +5만 |
| 새에만 | s07 ↔ amount · confirm~1 | +10만 |
| 새에만 | s07 ↔ amount · confirm~1 | 전액 |
| 새에만 | s07 ↔ amount · confirm~1 | ‹ ‹ |
| 새에만 | s07 ↔ amount · confirm~1 | ‹ |
| 새에만 | s07 ↔ amount · confirm~1 | 닫기 아이콘 |
| 새에만 | s07 ↔ amount · confirm~1 | ⌄ |
| 새에만 | s07 ↔ amount · confirm~1 | 다음 |
| 새에만 | s08 ↔ - | +1만 |
| 새에만 | s08 ↔ - | +5만 |
| 새에만 | s08 ↔ - | +10만 |
| 새에만 | s08 ↔ - | 전액 |
| 새에만 | s08 ↔ - | ‹ |
| 새에만 | s08 ↔ - | 닫기 아이콘 |
| 새에만 | s08 ↔ - | [금융거래한도계좌2]신한 주거래 우대 ⌄ 통장 계좌에서 |
| 새에만 | s08 ↔ - | ⌄ |
| 새에만 | s08 ↔ - | 10,000원 |
| 새에만 | s09 ↔ confirm | 김철수 받는분 메모 |
| 새에만 | s09 ↔ confirm | 내통장 메모 김철수 |
| 새에만 | s09 ↔ confirm | ‹ |
| 새에만 | s09 ↔ confirm | 닫기 아이콘 |
| 새에만 | s10 ↔ password | 닫기 아이콘 |
| 새에만 | s10 ↔ password | a-s10-02 |
| 새에만 | s10 ↔ password | a-s10-03 |
| 새에만 | s10 ↔ password | a-s10-04 |
| 새에만 | s10 ↔ password | a-s10-05 |
| 새에만 | s11 ↔ - | 닫기 아이콘 |
| 새에만 | s12 ↔ done | 확인 |

### 입력칸

| 나눔 | 화면 | 무엇 |
|---|---|---|
| 새에만 | s02 ↔ recipient | 계좌번호 직접 |
| 새에만 | s02 ↔ recipient | 입력 |
| 옛에만 | s04 ↔ account#2 · amount~1 · amount~2 | 계좌번호 110234567890 ⓧ |
| 옛에만 | s07 ↔ amount · confirm~1 | 얼마를 보낼까요? |
| 옛에만 | s07 ↔ amount · confirm~1 | 32,000원 |
| 새에만 | s08 ↔ - | 10,000원 |
| 다름 | s10 ↔ password | (빈 칸) ↔  |
| 새에만 | s10 ↔ password |  |
| 새에만 | s10 ↔ password |  |
| 새에만 | s10 ↔ password |  |

### 오류 경로

| 나눔 | 화면 | 무엇 |
|---|---|---|
| 캡처 없음 | error:wrong-bank | wrong-bank → err-bank |
