"""
네이버 검색광고 API - 키워드도구(RelKwdStat) 조회 스크립트

데이터랩 API와 다른 점: 이건 실제 월간 검색수(PC/모바일) 숫자를 그대로 준다.
블랙키위 화면에 나오는 "월간 검색량" 숫자가 이 API에서 나오는 것과 같은 종류.

사전 준비:
1. searchad.naver.com 로그인 -> 광고시스템 -> 도구 > API 사용관리
   -> 네이버 검색광고 API 서비스 신청
2. 발급받은 액세스라이선스(API_KEY) / 비밀키(SECRET_KEY) / 고객ID(CUSTOMER_ID)를
   .env 파일의 NAVER_ADS_API_KEY / NAVER_ADS_SECRET_KEY / NAVER_ADS_CUSTOMER_ID에 입력

인증 방식: HMAC-SHA256 서명 (요청마다 새로 생성해야 함, 데이터랩과 다름)
참고: https://github.com/naver/searchad-apidoc
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

CUSTOMER_ID = os.getenv("NAVER_ADS_CUSTOMER_ID")
API_KEY = os.getenv("NAVER_ADS_API_KEY")
SECRET_KEY = os.getenv("NAVER_ADS_SECRET_KEY")

BASE_URL = "https://api.naver.com"


def _make_signature(timestamp: str, method: str, uri: str, secret_key: str) -> str:
    message = f"{timestamp}.{method}.{uri}"
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _get_headers(method: str, uri: str) -> dict:
    timestamp = str(int(time.time() * 1000))
    signature = _make_signature(timestamp, method, uri, SECRET_KEY)
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": API_KEY,
        "X-Customer": str(CUSTOMER_ID),
        "X-Signature": signature,
    }


def get_keyword_volume(keywords: list[str]) -> list[dict]:
    """
    키워드(들)의 월간 검색수(PC/모바일)와 연관 키워드를 조회한다.
    keywords는 최대 5개까지 한 번에 넣을 수 있다 (콤마로 결합돼서 hintKeywords로 전달됨).

    주의: hintKeywords에 공백이 섞여 있으면 API가 400 에러(파라미터 유효하지 않음)를
    반환한다. 그래서 키워드 안의 공백은 자동으로 제거해서 보낸다.
    (참고: https://github.com/naver/searchad-apidoc/issues/1043)
    """
    uri = "/keywordstool"
    method = "GET"
    cleaned_keywords = [kw.replace(" ", "") for kw in keywords]
    params = {"hintKeywords": ",".join(cleaned_keywords), "showDetail": "1"}

    response = requests.get(
        BASE_URL + uri, params=params, headers=_get_headers(method, uri)
    )

    if response.status_code != 200:
        raise RuntimeError(f"API 요청 실패 (status={response.status_code}): {response.text}")

    return response.json().get("keywordList", [])


def save_result(rows: list[dict], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {output_path} ({len(rows)}건)")


if __name__ == "__main__":
    keywords = sys.argv[1:]
    if not keywords:
        print("사용법: python naver_searchad_keyword_tool.py 키워드1 키워드2 ...")
        raise SystemExit(1)
    if len(keywords) > 5:
        print(f"경고: 키워드는 최대 5개까지만 지원됩니다. 앞 5개만 사용합니다: {keywords[:5]}")
        keywords = keywords[:5]

    rows = get_keyword_volume(keywords)
    save_result(rows, "naver_searchad_keywords.json")

    # 블랙키위 화면과 같은 형태: 키워드 | PC 검색량 | 모바일 검색량 | 경쟁정도
    sorted_rows = sorted(
        rows, key=lambda r: r.get("monthlyPcQcCnt", 0) if isinstance(r.get("monthlyPcQcCnt", 0), int) else 0,
        reverse=True,
    )

    print(f"{'키워드':<20}{'PC 검색량':>12}{'모바일 검색량':>14}{'경쟁정도':>10}")
    print("-" * 58)
    for row in sorted_rows:
        print(
            f"{row.get('relKeyword', ''):<20}"
            f"{str(row.get('monthlyPcQcCnt', '-')):>12}"
            f"{str(row.get('monthlyMobileQcCnt', '-')):>14}"
            f"{row.get('compIdx', '-'):>10}"
        )

    # 엑셀에서 바로 열어볼 수 있게 CSV로도 저장
    import csv

    with open("naver_searchad_keywords.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["키워드", "PC 검색량", "모바일 검색량", "경쟁정도"])
        for row in sorted_rows:
            writer.writerow(
                [
                    row.get("relKeyword", ""),
                    row.get("monthlyPcQcCnt", ""),
                    row.get("monthlyMobileQcCnt", ""),
                    row.get("compIdx", ""),
                ]
            )
    print("\nCSV 저장 완료: naver_searchad_keywords.csv")
