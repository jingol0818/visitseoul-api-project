# 전수조사 분석 — items_ko.csv + details_ko.jsonl → census_report.md
import csv, json, re, sys, os, collections, datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
items = list(csv.DictReader(open(os.path.join(BASE, "items_ko.csv"), encoding="utf-8")))
details = {}
for line in open(os.path.join(BASE, "details_ko.jsonl"), encoding="utf-8"):
    try:
        d = json.loads(line); details[d["cid"]] = d
    except Exception:
        pass
cat_of = {r["cid"]: r["cat"] for r in items}
title_of = {r["cid"]: r["title"] for r in items}
out = []
P = out.append
P(f"# 비짓서울 API 표준 콘텐츠 전수조사 (한국어) — {datetime.date.today()}")
P(f"\n목록 항목 {len(items)} / 고유 cid {len(cat_of)} / 상세 수집 {len(details)}\n")

# 1. 카테고리별 건수·언어 수
P("## 1. 카테고리별 건수·다국어 보유")
P("| 카테고리 | 건수 | 평균 언어수 | 한국어만 | 7언어 전부 | 영 | 일 | 简 | 繁 | 러 | 말레이 |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
LANGS = ["영어", "일본어", "중국어 간체", "중국어 번체", "러시아어", "말레이어"]
tot_langs = collections.Counter()
for cat in sorted(set(cat_of.values()), key=lambda c: -sum(1 for r in items if r["cat"] == c)):
    rows = [r for r in items if r["cat"] == cat]
    n = len(rows)
    nl = [int(r["n_langs"]) for r in rows]
    only_ko = sum(1 for r in rows if int(r["n_langs"]) <= 1)
    all7 = sum(1 for r in rows if int(r["n_langs"]) >= 7)
    cnt = collections.Counter()
    for r in rows:
        for l in LANGS:
            if l in r["langs"]:
                cnt[l] += 1; tot_langs[l] += 1
    P(f"| {cat} | {n} | {sum(nl)/n:.1f} | {only_ko} ({only_ko/n:.0%}) | {all7} ({all7/n:.0%}) | " + " | ".join(f"{cnt[l]} ({cnt[l]/n:.0%})" for l in LANGS) + " |")
N = len(items)
P(f"| **합계** | {N} | | | | " + " | ".join(f"{tot_langs[l]} ({tot_langs[l]/N:.0%})" for l in LANGS) + " |")

# 2. 필드 채움률
P("\n## 2. 필드 채움률 (카테고리별, 상세 페이지 라벨 기준)")
labels = collections.Counter()
for d in details.values():
    for k in d["fields"]:
        labels[k] += 1
cats = sorted(set(cat_of.values()), key=lambda c: -sum(1 for r in items if r["cat"] == c))
P("| 필드 | 전체 | " + " | ".join(cats) + " |")
P("|---|---|" + "---|" * len(cats))
def filled(d, k):
    v = d["fields"].get(k, "")
    return bool(v and v.strip() and v.strip() not in ("-", "~"))
for k, _ in labels.most_common():
    row = []
    for cat in cats:
        ds = [d for c, d in details.items() if cat_of.get(c) == cat]
        f = sum(1 for d in ds if filled(d, k))
        row.append(f"{f/len(ds):.0%}" if ds else "-")
    allf = sum(1 for d in details.values() if filled(d, k))
    P(f"| {k} | {allf/len(details):.0%} | " + " | ".join(row) + " |")
# 좌표·이미지·내용 길이
P("\n추가 지표")
P(f"- 좌표 보유: {sum(1 for d in details.values() if d['lon'])/len(details):.0%}")
P(f"- 이미지 0장: {sum(1 for d in details.values() if d['n_img']==0)} / 평균 {sum(d['n_img'] for d in details.values())/len(details):.1f}장")
lens = sorted(d["len_content"] for d in details.values())
P(f"- 「내용」 길이 중앙값 {lens[len(lens)//2]}자 / 하위10% {lens[len(lens)//10]}자 / 200자 미만 {sum(1 for x in lens if x<200)}건")

# 3. 지역 분포 (주소)
P("\n## 3. 지역 분포 — 주소 첫 어절")
reg = collections.Counter(); gu = collections.Counter(); nonseoul = collections.defaultdict(list)
for c, d in details.items():
    a = d["fields"].get("주소", "")
    a2 = re.sub(r'^\(\d{5}\)\s*', '', a).strip()
    first = a2.split(" ")[0] if a2 else "(주소 없음)"
    reg[first] += 1
    if first.startswith("서울"):
        g = a2.split(" ")[1] if len(a2.split(" ")) > 1 else "?"
        gu[g] += 1
    elif a2:
        nonseoul[cat_of.get(c, "?")].append((title_of.get(c, ""), a2[:30]))
P("| 지역 | 건수 |"); P("|---|---|")
for k, v in reg.most_common(20): P(f"| {k} | {v} |")
P("\n서울 밖 콘텐츠(카테고리별): " + ", ".join(f"{k} {len(v)}" for k, v in nonseoul.items()))
for k, v in nonseoul.items():
    P(f"- {k}: " + " / ".join(f"{t}({a})" for t, a in v[:8]) + (" …" if len(v) > 8 else ""))
P("\n서울 자치구 분포(상위 25)")
P("| 자치구 | 건수 | " + " | ".join(cats) + " |"); P("|---|---|" + "---|" * len(cats))
for g, v in gu.most_common(25):
    row = []
    for cat in cats:
        row.append(str(sum(1 for c, d in details.items() if cat_of.get(c) == cat and re.sub(r'^\(\d{5}\)\s*', '', d["fields"].get("주소", "")).split(" ")[1:2] == [g])))
    P(f"| {g} | {v} | " + " | ".join(row) + " |")

# 4. 시간축 — 생성·수정일, 행사기간
P("\n## 4. 시간축")
cy = collections.Counter(d["created"][:4] for d in details.values() if d["created"])
uy = collections.Counter(d["updated"][:7] for d in details.values() if d["updated"])
P("생성 연도: " + ", ".join(f"{k} {v}" for k, v in sorted(cy.items())))
P("수정 월(최근 12): " + ", ".join(f"{k} {v}" for k, v in sorted(uy.items())[-12:]))
same = sum(1 for d in details.values() if d["created"] and d["created"] == d["updated"])
P(f"생성일=수정일(한 번도 수정 안 됨): {same} ({same/len(details):.0%})")
today = datetime.date.today()
ev = [d for c, d in details.items() if cat_of.get(c) == "축제/공연/행사"]
def parse_period(v):
    m = re.findall(r'(\d{4})\.(\d{2})\.(\d{2})', v)
    if not m: return None, None
    try:
        s = datetime.date(*map(int, m[0])); e = datetime.date(*map(int, m[-1]))
        return s, e
    except Exception:
        return None, None
past = fut = cur = nodate = 0
for d in ev:
    s, e = parse_period(d["fields"].get("일정정보", ""))
    if not s: nodate += 1
    elif e < today: past += 1
    elif s > today: fut += 1
    else: cur += 1
P(f"축제/공연/행사 {len(ev)}건: 종료됨 {past} / 진행 중 {cur} / 예정 {fut} / 기간 없음 {nodate}")
ends = collections.Counter()
for d in ev:
    s, e = parse_period(d["fields"].get("일정정보", ""))
    if e: ends[str(e.year)] += 1
P("행사 종료연도 분포: " + ", ".join(f"{k} {v}" for k, v in sorted(ends.items())))

# 5. 교통정보(지하철 도보거리)
P("\n## 5. 교통정보(지하철) — 거리 분포")
dist = []
for d in details.values():
    m = re.search(r'(\d{2,5})\s*m', d["fields"].get("교통정보", ""))
    if m: dist.append(int(m.group(1)))
if dist:
    dist.sort()
    P(f"거리 기재 {len(dist)}건 / 중앙값 {dist[len(dist)//2]}m / 90% {dist[int(len(dist)*.9)]}m / 1km 초과 {sum(1 for x in dist if x>1000)}건")
lines = collections.Counter()
for d in details.values():
    for l in re.findall(r'(\d호선|[가-힣]+선)', d["fields"].get("교통정보", "")):
        lines[l] += 1
P("노선 언급 상위: " + ", ".join(f"{k} {v}" for k, v in lines.most_common(12)))

# 6. 장애인 편의시설
P("\n## 6. 장애인 편의시설 값 분포")
fac = collections.Counter()
for d in details.values():
    for x in re.split(r'[,/·]\s*', d["fields"].get("장애인 편의시설", "")):
        x = x.strip()
        if x: fac[x] += 1
for k, v in fac.most_common(15): P(f"- {k}: {v}")

# 7. 태그
P("\n## 7. 태그 어휘 (상위 40)")
tags = collections.Counter()
for d in details.values():
    for t in d["tags"]:
        tags[t.strip()] += 1
P(", ".join(f"{k}({v})" for k, v in tags.most_common(40)))
P(f"태그 고유어휘 {len(tags)} / 태그 없는 콘텐츠 {sum(1 for d in details.values() if not d['tags'])}")

# 8. 음식 전용 필드
food = [d for c, d in details.items() if cat_of.get(c) == "음식"]
if food:
    P("\n## 8. 음식 전용 필드")
    kinds = collections.Counter(d["fields"].get("종류", "") for d in food)
    P("종류: " + ", ".join(f"{k or '(없음)'} {v}" for k, v in kinds.most_common(15)))
    price = collections.Counter(d["fields"].get("가격대", "") for d in food)
    P("가격대: " + ", ".join(f"{k or '(없음)'} {v}" for k, v in price.most_common(10)))
    foreign = sum(1 for d in food if "외국인" in d["fields"].get("이것만은 꼭!", ""))
    P(f"「이것만은 꼭!」에 외국인 언급: {foreign}건")

# 9. 「이것만은 꼭!」·cmmn_important 자유문 어휘
P("\n## 9. 「이것만은 꼭!」 자유문 키워드")
imp = collections.Counter()
for d in details.values():
    v = d["fields"].get("이것만은 꼭!", "")
    for kw in ["외국인", "영어", "중국어", "일본어", "예약", "주차", "반려", "휠체어", "카드", "현금", "할랄", "채식", "비건", "유아", "키즈", "포장", "배달", "와이파이", "무료"]:
        if kw in v: imp[kw] += 1
P(", ".join(f"{k} {v}" for k, v in imp.most_common()))

open(os.path.join(BASE, "census_report.md"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
