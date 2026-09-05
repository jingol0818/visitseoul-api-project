"""전수 수집 — 엔드포인트 4개를 순서대로 호출해 원본을 data/raw 에, 정제본을 data/processed 에 남긴다.

순서
 1. category_list  → data/raw/category_list.json      (하위 분류 전체·계층)
 2. lang_codes     → data/raw/lang_codes.json
 3. contents_list  → data/raw/list/{lang}_{cat}_p{n}.json  (8 카테고리 × 7 언어 × 전 페이지)
 4. contents_info  → data/raw/info/{cid}.json          (목록에서 얻은 모든 cid)
재실행하면 이미 받은 파일은 건너뛴다(중단 후 재개 가능).

실행:  python -m census.fetch_all [--langs ko,en] [--cats Cv7s8m5] [--no-info]
"""
import argparse
import json
import sys
from pathlib import Path

from . import config
from .client import VisitSeoulClient

sys.stdout.reconfigure(encoding="utf-8")


def save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default=",".join(config.LANGS))
    ap.add_argument("--cats", default=",".join(config.CATEGORIES.values()))
    ap.add_argument("--no-info", action="store_true", help="목록만 수집")
    a = ap.parse_args()
    c = VisitSeoulClient()

    # 1·2 코드표
    cat_path = config.DATA_RAW / "category_list.json"
    if not cat_path.exists():
        save(cat_path, c.call("category_list"))
    lang_path = config.DATA_RAW / "lang_codes.json"
    if not lang_path.exists():
        save(lang_path, c.call("lang_codes"))
    langs_known = [x.get("code_id") for x in json.loads(lang_path.read_text(encoding="utf-8")).get("data", [])]
    print("언어 코드(API):", langs_known)

    # 3 목록
    index = []  # (lang, cat, cid)
    for lang in a.langs.split(","):
        for cat in a.cats.split(","):
            p = 1
            while True:
                fp = config.DATA_RAW / "list" / f"{lang}_{cat}_p{p}.json"
                if fp.exists():
                    res = json.loads(fp.read_text(encoding="utf-8"))
                else:
                    res = c.contents_list(cat, lang, page_no=p)
                    save(fp, res)
                data = res.get("data") or []
                for it in data:
                    index.append({"lang": lang, "cat": cat, "cid": it.get("cid"), "post_sj": it.get("post_sj"),
                                  "updt_dt_text": it.get("updt_dt_text"), "creat_dt_text": it.get("creat_dt_text")})
                paging = res.get("paging") or {}
                total = paging.get("total_count", 0); size = paging.get("page_size") or len(data) or 1
                if p == 1:
                    print(f"[{lang}] {cat}: total={total} page_size={size}")
                if not data or p * size >= total:
                    break
                p += 1
    idx_path = config.DATA_OUT / "index_all.jsonl"
    idx_path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in index), encoding="utf-8")
    print(f"목록 인덱스 {len(index)}행 → {idx_path}")

    # 4 상세
    if a.no_info:
        return
    cids = sorted({x["cid"] for x in index if x["cid"]})
    for i, cid in enumerate(cids, 1):
        fp = config.DATA_RAW / "info" / f"{cid}.json"
        if fp.exists():
            continue
        save(fp, c.contents_info(cid))
        if i % 200 == 0:
            print(f"  info {i}/{len(cids)}")
    print("상세 수집 완료:", len(cids))


if __name__ == "__main__":
    main()
