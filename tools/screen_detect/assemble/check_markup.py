r"""조립 1단계 - 마크업 출력 검사 (규칙 마크업 · 2단계 LLM 마크업에 같이 쓴다).

  ① 모든 요소 id 가 data-src 로 한 번씩
  ② data-src 없는 보이는 글 · 버튼 · 그림 자리가 없다 (그릇 · 띠 · 구역 div 는 된다)
  ③ data-src 요소 바로 안의 글은 그 요소의 text 또는 text_fixed 그대로 (꺾쇠는 그 글자, 글을 지운 것은 빈 글)
  ④ 그림 자리는 .pic[role=img][aria-label] (aria-label 이 비지 않음)
  ⑤ 꺾쇠로 정한 요소는 글자 (› ⌄ ⌃ ‹) 이고 그림 자리를 품지 않는다
check(html, expected) → {"ok": bool, "problems": [{"rule", "id", "why"}]}. expected 는 요소 id →
{"text": 보여야 할 바로 안 글 (None 이면 보지 않음), "chevron": 글자 또는 None}.
"""
import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
GLYPHS = {"›", "⌄", "⌃", "‹"}


def norm(s):
    return re.sub(r"\s+", "", s or "")


class _Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []            # (tag, attrs, data-src 또는 None)
        self.src = {}              # id → 횟수
        self.own = {}              # id → 바로 안 글
        self.pics = {}             # id → 안에 품은 그림 자리 수
        self.problems = []
        self.in_body = False

    def _src_ancestor(self):
        return next((s for _, _, s in reversed(self.stack) if s), None)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "body":
            self.in_body = True
        src = a.get("data-src")
        if src:
            self.src[src] = self.src.get(src, 0) + 1
            self.own.setdefault(src, "")
            self.pics.setdefault(src, 0)
        cls = (a.get("class") or "").split()
        is_pic = "pic" in cls or a.get("role") == "img"
        if is_pic:
            if a.get("role") != "img" or not (a.get("aria-label") or "").strip() or "pic" not in cls:
                self.problems.append({"rule": "④", "id": src or self._src_ancestor(),
                                      "why": "그림 자리가 .pic[role=img][aria-label] 꼴이 아니다"})
            for s in [x for _, _, x in self.stack if x] + ([src] if src else []):
                self.pics[s] = self.pics.get(s, 0) + 1
        pressable = tag == "button" or a.get("role") == "button" or "data-action" in a
        if self.in_body and (pressable or is_pic) and not src and not self._src_ancestor():
            self.problems.append({"rule": "②", "id": None,
                                  "why": "data-src 없는 %s (%s)" % ("버튼" if pressable else "그림 자리", tag)})
        if tag not in VOID:
            self.stack.append((tag, a, src))

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break

    def handle_data(self, data):
        if not self.in_body or not data.strip():
            return
        if any(t in ("script", "style") for t, _, _ in self.stack):
            return
        top = self.stack[-1][2] if self.stack else None
        if top:
            self.own[top] += data
        elif not self._src_ancestor():
            self.problems.append({"rule": "②", "id": None, "why": "data-src 밖의 보이는 글: %r" % data.strip()[:30]})
        else:
            # data-src 요소 안의 꾸밈 그릇 (span 등) 의 글 - 가장 가까운 data-src 의 글로 센다
            self.own[self._src_ancestor()] += data


def check(html, expected):
    sc = _Scan()
    sc.feed(html)
    probs = list(sc.problems)
    for i in expected:
        n = sc.src.get(i, 0)
        if n != 1:
            probs.append({"rule": "①", "id": i, "why": "data-src 가 %d번" % n})
    for i in sc.src:
        if i not in expected:
            probs.append({"rule": "①", "id": i, "why": "요소 목록에 없는 data-src"})
    for i, want in expected.items():
        if i not in sc.src:
            continue
        got = norm(sc.own.get(i))
        if want.get("chevron"):
            if got != norm(want["chevron"]) or sc.pics.get(i):
                probs.append({"rule": "⑤", "id": i, "why": "꺾쇠인데 글자 %r · 그림 자리 %d" % (got, sc.pics.get(i, 0))})
            continue
        if want.get("text") is not None and got != norm(want["text"]):
            probs.append({"rule": "③", "id": i, "why": "글 %r ≠ %r" % (got[:30], norm(want["text"])[:30])})
    return {"ok": not probs, "problems": probs}
