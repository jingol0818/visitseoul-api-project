"""비짓서울 API 최소 클라이언트. 키는 환경변수에서만 읽고, 원본 응답을 그대로 저장한다."""
import json
import time
from typing import Any

import requests

from . import config


class VisitSeoulClient:
    def __init__(self, api_key: str | None = None, sleep: float | None = None):
        self.api_key = api_key or config.API_KEY
        if not self.api_key:
            raise RuntimeError("VISITSEOUL_API_KEY 환경변수가 비어 있다. .env.example 을 참고해 .env 를 만든다.")
        self.sleep = config.SLEEP if sleep is None else sleep
        self.s = requests.Session()
        self.s.headers.update({
            "VISITSEOUL-API-KEY": self.api_key,
            "Accept": "application/json;charset=UTF-8",
            "Content-Type": "application/json;charset=UTF-8",
        })

    def call(self, name: str, **params: Any) -> dict:
        ep = config.ENDPOINTS[name]
        url = config.HOST + ep["path"]
        unknown = set(params) - set(ep["params"])
        if unknown:
            raise ValueError(f"{name}: 명세에 없는 파라미터 {unknown}")
        for attempt in range(3):
            try:
                if ep["method"] == "GET":
                    r = self.s.get(url, params=params or None, timeout=30)
                else:
                    r = self.s.post(url, data=json.dumps(params), timeout=30)
                time.sleep(self.sleep)
                if r.status_code == 429:
                    time.sleep(10 * (attempt + 1)); continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                time.sleep(3 * (attempt + 1))
        raise RuntimeError("unreachable")

    # 편의 메서드
    def categories(self) -> list[dict]:
        return self.call("category_list").get("data", [])

    def lang_codes(self) -> list[dict]:
        return self.call("lang_codes").get("data", [])

    def contents_list(self, com_ctgry_sn: str, lang_code_id: str, page_no: int = 1,
                      keyword: str | None = None, sort_type: str = "latest") -> dict:
        p = {"com_ctgry_sn": com_ctgry_sn, "lang_code_id": lang_code_id, "page_no": page_no, "sort_type": sort_type}
        if keyword:
            p["keyword"] = keyword
        return self.call("contents_list", **p)

    def contents_info(self, cid: str) -> dict:
        return self.call("contents_info", cid=cid)
