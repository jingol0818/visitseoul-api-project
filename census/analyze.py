"""전수조사 분석 — data/raw 원본을 읽어 data/processed 정제본과 reports/census_report.md 를 만든다.

조사 항목
 1. 엔드포인트·요청 파라미터 목록(명세 기준, config.ENDPOINTS)
 2. 응답 필드 전체(실제 응답 키의 합집합 vs 명세 28필드)
 3. 8개 카테고리별 데이터 수(하위 분류 포함)
 4. 7개 언어별 데이터 수·언어 간 cid 매핑(multi_lang_list)
 5. 필드별 값 존재율(null/빈값/빈배열 비율) — 카테고리×언어
 6. 주요 필드 충실도: 좌표·운영시간·휴무일·행사기간·장애인 편의시설·교통·태그
 7. 등록일/수정일 분포·갱신 특성(생성=수정 비율, 최근 수정 월별)
 8. 서울 외 지역 콘텐츠(주소 첫 어절이 서울이 아닌 것)
 9. 이상현상: 중복 제목, 종료된 행사 잔존, 언어 간 필드 불일치(같은 cid 계열의 좌표·기간·전화 차이)
실행:  python -m census.analyze
"""
import collections
import datetime as dt
import json
import re
import sys

import pandas as pd

from . import config

sys.stdout.reconfigure(encoding="utf-8")


def load_infos() -> pd.DataFrame:
    rows = []
    for fp in (config.DATA_RAW / "info").glob("*.json"):
        d = json.loads(fp.read_text(encoding="utf-8")).get("data") or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        d["_file"] = fp.name
        rows.append(d)
    df = pd.DataFrame(rows)
    df.to_csv(config.DATA_OUT / "info_all.csv", index=False, encoding="utf-8-sig")
    return df


def empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return str(v).strip() in ("", "-", "null", "None")


def main() -> None:
    out = []
    P = out.append
    P(f"# 비짓서울 API 전수조사 리포트 — {dt.date.today()}\n")

    # 1. 엔드포인트
    P("## 1. 엔드포인트·요청 파라미터")
    for k, v in config.ENDPOINTS.items():
        P(f"- `{v['method']} {v['path']}` ({k}) — 파라미터: {', '.join(v['params']) or '없음'}")

    df = load_infos()
    if df.empty:
        P("\n(상세 원본 없음 — fetch_all 을 먼저 실행)")
        (config.REPORTS / "census_report.md").write_text("\n".join(out), encoding="utf-8")
        print("\n".join(out)); return

    # 2. 응답 필드
    keys = [c for c in df.columns if not c.startswith("_")]
    P(f"\n## 2. 응답 필드 — 실제 {len(keys)}개 / 명세 {len(config.INFO_FIELDS)}개")
    P("명세에 없는 실제 키: " + ", ".join(sorted(set(keys) - set(config.INFO_FIELDS))) )
    P("실제 응답에 없는 명세 키: " + ", ".join(sorted(set(config.INFO_FIELDS) - set(keys))))

    # 3·4 카테고리·언어
    df["cat1"] = df["cate_depth"].apply(lambda x: (x[0] if isinstance(x, list) and x else str(x).split(">")[0]).strip() if not empty(x) else "")
    P("\n## 3. 카테고리(대분류)×언어 건수")
    ct = pd.crosstab(df["cat1"], df["lang_code_id"], margins=True)
    P(ct.to_markdown())
    P("\n## 4. 언어 간 매핑 — multi_lang_list 언어 수 분포")
    nl = df["multi_lang_list"].apply(lambda x: 0 if empty(x) else len(str(x).split(",")))
    P(nl.value_counts().sort_index().to_frame("건수").to_markdown())

    # 5·6 필드 존재율
    P("\n## 5. 필드별 값 존재율(카테고리별, 한국어 기준)")
    ko = df[df["lang_code_id"] == "ko"] if "lang_code_id" in df else df
    rows = {}
    for f in config.INFO_FIELDS:
        if f not in ko:
            continue
        rows[f] = {c: f"{(~g[f].apply(empty)).mean():.0%}" for c, g in ko.groupby("cat1")}
        rows[f]["전체"] = f"{(~ko[f].apply(empty)).mean():.0%}"
    P(pd.DataFrame(rows).T.to_markdown())
    P("\n## 6. 주요 필드 충실도(전 언어)")
    for f in ["map_position_x", "cmmn_use_time", "closed_days", "schdul_info_bgnde", "disabled_facility", "subway_info", "tag", "cmmn_important"]:
        if f in df:
            P(f"- {f}: 존재 {(~df[f].apply(empty)).mean():.0%}")

    # 7. 시간축
    P("\n## 7. 등록일/수정일")
    cy = df["creat_dt_text"].astype(str).str[:4].value_counts().sort_index()
    P("생성 연도: " + ", ".join(f"{k} {v}" for k, v in cy.items()))
    um = df["updt_dt_text"].astype(str).str[:7].value_counts().sort_index().tail(12)
    P("최근 수정 월: " + ", ".join(f"{k} {v}" for k, v in um.items()))
    same = (df["creat_dt_text"] == df["updt_dt_text"]).mean()
    P(f"생성일=수정일 비율: {same:.0%}")
    today = dt.date.today()
    ev = df[~df["schdul_info_endde"].apply(empty)].copy()
    if not ev.empty:
        end = pd.to_datetime(ev["schdul_info_endde"].astype(str).str.replace(".", "-", regex=False), errors="coerce").dt.date
        P(f"행사기간 보유 {len(ev)}건 중 종료일 경과 {(end < today).sum()}건")

    # 8. 서울 외
    P("\n## 8. 서울 외 지역 콘텐츠")
    addr = df["new_adres"].fillna(df.get("adres")).astype(str).str.replace(r"^\(\d{5}\)\s*", "", regex=True)
    first = addr.str.split(" ").str[0]
    P(first.value_counts().head(15).to_frame("건수").to_markdown())
    non = df[~first.str.startswith("서울") & ~addr.isin(["", "nan", "None"])]
    P(f"서울 밖(주소 기준): {len(non)}건 / 카테고리별 " + ", ".join(f"{k} {v}" for k, v in non["cat1"].value_counts().items()))

    # 9. 이상현상
    P("\n## 9. 이상현상")
    dup = ko.groupby(["cat1", "post_sj"]).size()
    P(f"- 같은 카테고리 내 동일 제목: {(dup > 1).sum()}건")
    base = df["cid"].astype(str).str[2:]  # 언어 접두(KO/EN/JP/CN/TC/RU/MS) 제거 → 계열 키
    df["_series"] = base
    mism = 0
    for s, g in df.groupby("_series"):
        if len(g) > 1:
            for f in ["map_position_x", "schdul_info_bgnde", "cmmn_telno"]:
                if f in g and g[f].astype(str).nunique() > 1:
                    mism += 1
                    break
    P(f"- 언어 간 좌표·기간·전화 불일치 계열: {mism}건")
    (config.REPORTS / "census_report.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
