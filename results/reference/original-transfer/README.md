# 참고 자료 — 이체 원본을 빌드로 둔 화면설계서

**무엇.** 재구성 실행이 아니다. 이체 과제의 원본 HTML(`inputs/original_transfer.html`)을 그대로
"빌드" 로, 원본 흐름(`flows/original.json`)을 그대로 흐름 명세로 두고 만든 화면설계서다
(`storyboard/storyboard.json`, schema 3). 장 11 (화면 10) · 항목 66. 그림은 재현 HTML 을 로우파이
덮개로 찍은 것이다 (실제 앱 · 더미앱 캡처가 아니다).

**쓰는 곳.** Figma 플러그인으로 원본의 그림 자리(로고 · 아이콘 자리, 장마다 `images`)가 어디에
어떤 크기로 그려지는지 확인한다 — 장마다 home 19 · recipient 3 · bank 38 · confirm 1 (모두
`original: true`, 이름 60개 = 검사 L 의 원본 집합).

**어떻게 만들었나.** 원본 대 원본을 검사기로 한 번 판정하고(루프와 같은 길, 통과), 화면설계서를
만든다. 영역 묶기는 `--mock` (정해진 답 — 모델을 부르지 않는다), PDF 는 만들지 않았다. 만든 뒤
`storyboard/` 만 남기고 임시 실행 폴더의 나머지는 지웠다.

**다시 만들기** (저장소 맨 위에서, PowerShell):

```powershell
.\.venv\Scripts\python.exe tools/reference_storyboard.py --task transfer --out results/reference/original-transfer
```

`storyboard/` 를 지우고 다시 쓴다. 이 README 는 그대로 둔다.
