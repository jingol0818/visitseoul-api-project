# 비짓서울 API 표준 콘텐츠 전수조사 크롤러 (웹 목록·상세, 로그인 불필요)
# 원본 HTML을 raw/ 에 보존하고, 파싱 결과를 items_<lang>.csv / details_ko.jsonl 로 낸다. 재실행 시 이미 받은 파일은 건너뛴다.
import re, sys, os, time, json, csv, math, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
RAW_L = os.path.join(BASE, "raw", "list"); RAW_V = os.path.join(BASE, "raw", "view")
os.makedirs(RAW_L, exist_ok=True); os.makedirs(RAW_V, exist_ok=True)
CATS = {"문화관광":"Ca0o2d4","쇼핑":"Cu8e6t5","숙박":"Ch4v8z7","역사관광":"Ca1z6p7",
        "음식":"Cl9s3y9","자연관광":"Co6c2n2","체험관광":"Cc9i5o2","축제/공연/행사":"Cv7s8m5"}
SLEEP = 0.35
UA = {"User-Agent": "Mozilla/5.0 (contest-harness census; contact via api.visitseoul.net 1:1)"}
ITEM_RE = re.compile(r'<li>\s*<a href="javascript:goViewPage\(\'([A-Za-z0-9]+)\'\);" class="board-link"[\s\S]*?<div class="path[^"]*">([\s\S]*?)</div>[\s\S]*?<h3 class="mt-10">([^<]*)</h3>[\s\S]*?<div class="btn-lang">([\s\S]*?)</div>\s*</li>')
LANG_RE = re.compile(r"goViewPage\('([A-Za-z0-9]+)'\)[^>]*>\s*([^\s<]+)<span class=\"sr-only\">([^<]*)</span>")

def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return open(path, encoding="utf-8", errors="replace").read(), True
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, headers=UA)
            h = urllib.request.urlopen(r, timeout=40).read().decode("utf-8", "replace")
            open(path, "w", encoding="utf-8").write(h)
            time.sleep(SLEEP)
            return h, False
        except Exception as e:
            print("  retry", attempt, url, e, flush=True); time.sleep(2 + attempt * 3)
    open(path + ".fail", "w").write(url)
    return "", False

def crawl_lists(lang):
    out = os.path.join(BASE, f"items_{lang}.csv")
    rows = []
    for cat, code in CATS.items():
        h, _ = get(f"https://api.visitseoul.net/contents/standard/list?lang=ko&lang_code={lang}&com_ctgry={code}&pageNo=1",
                   os.path.join(RAW_L, f"{lang}_{code}_p1.html"))
        m = re.search(r'총<strong>([0-9,]+)</strong>', h)
        total = int(m.group(1).replace(",", "")) if m else 0
        pages = max(1, math.ceil(total / 20))
        print(f"[{lang}] {cat} total={total} pages={pages}", flush=True)
        for p in range(1, pages + 1):
            h, cached = get(f"https://api.visitseoul.net/contents/standard/list?lang=ko&lang_code={lang}&com_ctgry={code}&pageNo={p}",
                            os.path.join(RAW_L, f"{lang}_{code}_p{p}.html"))
            items = ITEM_RE.findall(h)
            if not items:
                print(f"  ⚠ page {p} items=0", flush=True)
            for cid, path, title, langblk in items:
                sub = re.sub(r"<[^>]+>", "", path); sub = re.sub(r"\s+", " ", sub).strip()
                langs = LANG_RE.findall(langblk)
                rows.append({"cid": cid, "title": title.strip(), "cat": cat, "cat_path": sub, "page": p,
                             "langs": "|".join(f"{c}:{n}" for c, _, n in langs), "n_langs": len(langs)})
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"[{lang}] items={len(rows)} unique={len(set(r['cid'] for r in rows))} → {out}", flush=True)
    return rows

def parse_view(h, cid):
    d = {"cid": cid}
    m = re.search(r'<!--s : 상세보기 헤더-->([\s\S]*?)<!--e : 상세보기 헤더-->', h)
    head = m.group(1) if m else h[:20000]
    t = re.search(r'<h3[^>]*>([^<]+)</h3>', head); d["title"] = t.group(1).strip() if t else ""
    d["created"] = (re.search(r'생성일\s*:\s*([0-9.]+)', h) or [None, ""])[1]
    d["updated"] = (re.search(r'수정일\s*:\s*([0-9.]+)', h) or [None, ""])[1]
    d["langs"] = "|".join(f"{c}:{n}" for c, _, n in LANG_RE.findall(head))
    d["n_img"] = len(re.findall(r'srvcId=MEDIA&parentSn=\d+&fileTy=MEDIA', head))
    fields = {}
    for dt, dd in re.findall(r'<dl>\s*<dt>\s*([^<]+?)\s*</dt>\s*<dd[^>]*>([\s\S]*?)</dd>\s*</dl>', h):
        v = re.sub(r'<style[\s\S]*?</style>', '', dd)
        v = re.sub(r'<[^>]+>', ' ', v); v = re.sub(r'\s+', ' ', v).strip()
        fields[dt.strip()] = v
    d["fields"] = fields
    d["tags"] = re.findall(r'#\s*([^#<\n]+?)\s*(?=#|</)', fields.get("태그", "")) if "태그" in fields else []
    lon = re.search(r'경도\s*:\s*([0-9.]+)', h); lat = re.search(r'위도\s*:\s*([0-9.]+)', h)
    d["lon"] = lon.group(1) if lon else ""; d["lat"] = lat.group(1) if lat else ""
    d["len_content"] = len(fields.get("내용", ""))
    return d

def crawl_details(rows):
    out = os.path.join(BASE, "details_ko.jsonl")
    done = set()
    if os.path.exists(out):
        for line in open(out, encoding="utf-8"):
            try: done.add(json.loads(line)["cid"])
            except: pass
    cids = [r["cid"] for r in rows]
    seen = set(); todo = [c for c in cids if not (c in seen or seen.add(c)) and c not in done]
    print(f"details: total={len(set(cids))} done={len(done)} todo={len(todo)}", flush=True)
    with open(out, "a", encoding="utf-8") as f:
        for i, cid in enumerate(todo, 1):
            h, _ = get(f"https://api.visitseoul.net/contents/standard/view/{cid}?lang=ko", os.path.join(RAW_V, f"{cid}.html"))
            if not h: continue
            f.write(json.dumps(parse_view(h, cid), ensure_ascii=False) + "\n"); f.flush()
            if i % 100 == 0: print(f"  {i}/{len(todo)}", flush=True)
    print("details done", flush=True)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "lists"):
        rows = crawl_lists("ko")
    else:
        rows = list(csv.DictReader(open(os.path.join(BASE, "items_ko.csv"), encoding="utf-8")))
    if mode in ("all", "details"):
        crawl_details(rows)
    if mode in ("all", "en"):
        crawl_lists("en")
