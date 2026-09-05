"""엔드포인트·상수 정의. 비밀값은 여기 두지 않는다 — 환경변수에서만 읽는다."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # .env 가 있으면 읽는다(저장소에는 .env.example 만 둔다)
    load_dotenv()
except ImportError:
    pass

API_KEY = os.environ.get("VISITSEOUL_API_KEY", "")
SLEEP = float(os.environ.get("VISITSEOUL_SLEEP", "0.5"))
HOST = "https://api-call.visitseoul.net"

# 비짓서울 API 센터 명세(api.visitseoul.net > API 안내 > API 목록) 기준, 2026-09-05 확인
ENDPOINTS = {
    "category_list": {"method": "GET",  "path": "/api/v1/category/list", "params": []},
    "lang_codes":    {"method": "GET",  "path": "/api/v1/code/lang",     "params": []},
    "contents_list": {"method": "POST", "path": "/api/v1/contents/list",
                      "params": ["com_ctgry_sn", "lang_code_id", "keyword", "sort_type", "page_no"]},
    "contents_info": {"method": "POST", "path": "/api/v1/contents/info", "params": ["cid"]},
}

# 대분류 8개 (홈 화면 링크의 com_ctgry 값). category_list 호출로 하위 분류까지 다시 확인한다
CATEGORIES = {
    "문화관광": "Ca0o2d4", "쇼핑": "Cu8e6t5", "숙박": "Ch4v8z7", "역사관광": "Ca1z6p7",
    "음식": "Cl9s3y9", "자연관광": "Co6c2n2", "체험관광": "Cc9i5o2", "축제/공연/행사": "Cv7s8m5",
}
# 언어 코드는 lang_codes 호출 결과로 대체한다. 아래는 명세·웹 화면에서 확인한 기본값
LANGS = ["ko", "en", "ja", "zh-CN", "zh-TW", "ru", "ms"]

# 콘텐츠 정보(contents_info) 응답 필드 — 명세 기준 28개. 채움률 계산의 기준 목록
INFO_FIELDS = [
    "cid", "lang_code_id", "com_ctgry_sn", "cate_depth", "multi_lang_list", "main_img", "relate_img",
    "post_sj", "sumry", "schdul_info_bgnde", "schdul_info_endde", "creat_dt_text", "updt_dt_text", "tag",
    "cmmn_telno", "cmmn_hmpg_url", "cmmn_use_time", "cmmn_important", "disabled_facility", "closed_days",
    "adres", "new_zip_code", "new_adres", "map_position_x", "map_position_y", "subway_info", "post_desc",
]

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"        # 원본 JSON (gitignore)
DATA_OUT = ROOT / "data" / "processed"  # 정제 CSV/JSONL
REPORTS = ROOT / "reports"              # 분석 리포트(md)
for p in (DATA_RAW, DATA_OUT, REPORTS):
    p.mkdir(parents=True, exist_ok=True)
