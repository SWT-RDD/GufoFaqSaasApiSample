"""GufoFAQ API 範例程式：以 API 金鑰呼叫資料上傳 API 與文字萃取 API。

使用方式比照舊版範例：在最下面「主程式」區塊解除想執行那一段的註解，再執行
    pip install -r requirements.txt
    python sample.py

各支 API 的欄位與錯誤說明見 README.md。
"""

import json
from contextlib import ExitStack
from pathlib import Path

import requests

# ── 共用設定 ─────────────────────────────────────────────────────────────
BASE_URL = "https://your-host"  # 請在此替換成貴單位使用的網址（結尾不要加 /）
API_KEY = "your_api_key"  # 請在此替換成你的 API 金鑰（後台「設定 → 萃取 API 金鑰」）

# 如果碰到 SSL 憑證問題（例如測試環境的自簽憑證），可以暫時改成 False
VERIFY_TLS = True

# 上傳是逐筆處理，資料量大時回應較久，讀取逾時要設長一點：(連線逾時, 讀取逾時) 秒
TIMEOUT = (10, 600)

session = requests.Session()
session.verify = VERIFY_TLS


def api_key_headers() -> dict:
    """每個請求都要帶的 API 金鑰標頭。"""
    return {"X-API-Key": API_KEY}


# ── 錯誤處理 ─────────────────────────────────────────────────────────────
def print_error(resp: requests.Response) -> None:
    """印出錯誤。錯誤回應有幾種形狀（見 README「錯誤格式」），這裡全部收成 code ＋ 訊息。"""
    code, message = None, resp.text
    try:
        body = resp.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, dict):  # {"detail": {"code": ..., "detail": ...}}
            code, message = detail.get("code"), detail.get("detail")
        elif isinstance(detail, list):  # 422 欄位驗證失敗
            code = "validation_error"
            message = "; ".join(f"{'.'.join(map(str, e.get('loc', [])))}: {e.get('msg')}" for e in detail)
        else:  # {"detail": "..."}、{"code": ..., "detail": ...}、{"error": ..., "code": ...}
            code = body.get("code")
            message = detail if detail is not None else body.get("error")

    code_part = f", Code: {code}" if code else ""
    print(f"Handled Error: HTTP {resp.status_code}{code_part}, Message: {message}")
    if resp.headers.get("Retry-After"):
        print(f"  請在 {resp.headers['Retry-After']} 秒後重試")
    if resp.headers.get("X-Correlation-ID"):
        print(f"  關聯編號：{resp.headers['X-Correlation-ID']}（回報問題時請提供）")


# ── 1. 資料上傳 API ──────────────────────────────────────────────────────
def create_dataset(name: str, description: str | None = None) -> int | None:
    """建立資料集，回傳資料集編號。"""
    resp = session.post(
        f"{BASE_URL}/api/v1/datasets",
        json={"name": name, "description": description},
        headers=api_key_headers(),
        timeout=TIMEOUT,
    )
    if not resp.ok:
        print_error(resp)
        return None
    data = resp.json()
    print(f"建立成功：id={data['id']}  name={data['name']}")
    return data["id"]


def list_datasets() -> None:
    """列出帳號裡所有資料集。"""
    resp = session.get(f"{BASE_URL}/api/v1/datasets", headers=api_key_headers(), timeout=TIMEOUT)
    if not resp.ok:
        print_error(resp)
        return
    for ds in resp.json():
        print(f"id={ds['id']}  name={ds['name']}  file_count={ds['file_count']}")


def delete_dataset(dataset_id: int) -> None:
    """刪除整個資料集（無法復原）。"""
    resp = session.delete(f"{BASE_URL}/api/v1/datasets/{dataset_id}", headers=api_key_headers(), timeout=TIMEOUT)
    if not resp.ok:
        print_error(resp)
        return
    print(f"已刪除資料集 {resp.json()['deleted']}")


def print_results(data: dict) -> None:
    """印出上傳結果。每一筆各自成功或失敗，HTTP 200 不代表每一筆都成功。"""
    print(f"新增 {data['inserted']} 筆、取代 {data['updated']} 筆、失敗 {data['failed']} 筆")
    for i, r in enumerate(data["results"]):
        name = r.get("filename", f"第 {i + 1} 筆")
        if r["ok"]:
            # doc（結構化資料）或 file_id（檔案）就是之後刪除要用的編號，建議存起來
            item_id = r.get("doc", r.get("file_id"))
            state = r.get("sync_state", {}).get("state")
            print(f"  {name}：成功  編號={item_id}  處理狀態={state}")
        else:
            code_part = f"Code={r['code']}  " if r.get("code") else ""
            print(f"  {name}：失敗  {code_part}{r.get('error')}")


def upload_records(dataset_id: int, records: list[dict], convert_html: bool = True) -> None:
    """上傳結構化資料，每一筆成為一份文件。"""
    resp = session.post(
        f"{BASE_URL}/api/v1/datasets/{dataset_id}/records",
        json={"records": records, "convert_html": convert_html},
        headers=api_key_headers(),
        timeout=TIMEOUT,
    )
    if not resp.ok:
        print_error(resp)
        return
    print_results(resp.json())


def upload_files(
    dataset_id: int,
    paths: list[str],
    mapping: dict | None = None,
    external_keys: dict | None = None,
    header_rows: int = 1,
) -> None:
    """上傳 pdf／docx／xlsx 檔案。

    mapping（只對 xlsx 有效）：{"content": ["答案"], "title": ["問題"]}，帶了就是每一列一筆。
    external_keys：{"檔名": "外部主鍵"}，帶了就會取代同主鍵的舊檔案。
    """
    form = {"header_rows": str(header_rows)}
    if mapping:
        form["mapping"] = json.dumps(mapping, ensure_ascii=False)
    if external_keys:
        form["external_keys"] = json.dumps(external_keys, ensure_ascii=False)

    with ExitStack() as stack:
        files = [("files", (Path(p).name, stack.enter_context(open(p, "rb")))) for p in paths]
        resp = session.post(
            f"{BASE_URL}/api/v1/datasets/{dataset_id}/files",
            data=form,
            files=files,
            headers=api_key_headers(),
            timeout=TIMEOUT,
        )
    if not resp.ok:
        print_error(resp)
        return
    print_results(resp.json())


def list_records(dataset_id: int) -> None:
    """列出資料集裡的每一份資料與檔案。"""
    resp = session.get(
        f"{BASE_URL}/api/v1/datasets/{dataset_id}/records", headers=api_key_headers(), timeout=TIMEOUT
    )
    if not resp.ok:
        print_error(resp)
        return
    for f in resp.json()["files"]:
        print(f"id={f['id']}  {f['filename']}  type={f['file_type']}  records={f['record_count']}  {f['uploaded_at']}")


def delete_record(dataset_id: int, file_id: int) -> None:
    """刪除一份資料或一個檔案。file_id 是上傳時拿到的 doc／file_id。"""
    resp = session.delete(
        f"{BASE_URL}/api/v1/datasets/{dataset_id}/records/{file_id}", headers=api_key_headers(), timeout=TIMEOUT
    )
    if not resp.ok:
        print_error(resp)
        return
    print(f"已刪除 {resp.json()['deleted']}")


# ── 2. 文字萃取 API ──────────────────────────────────────────────────────
def extract_country_or_time(text: str, mode: int, time_reference: str | None = None) -> None:
    """萃取國家及／或時間。mode：1＝國家、2＝時間、3＝兩者。每次呼叫扣一次萃取次數。"""
    body = {"text": text, "mode": mode}
    if time_reference:
        body["time_reference"] = time_reference
    resp = session.post(
        f"{BASE_URL}/api/extract/country-or-time", json=body, headers=api_key_headers(), timeout=TIMEOUT
    )
    if not resp.ok:
        print_error(resp)
        return
    result = resp.json()
    print("=== 萃取結果 ===")
    print(f"國家: {result['country']}")
    print(f"時間: {result['time']}")


# ── 主程式 ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 主程式（資料上傳 - 列出資料集）
    # ----------------------------------------------------------
    list_datasets()
    # ----------------------------------------------------------

    # 主程式（資料上傳 - 建立資料集）
    # ----------------------------------------------------------
    # dataset_id = create_dataset("API 範例資料集", "示範用的常見問題")
    # ----------------------------------------------------------

    # 主程式（資料上傳 - 上傳結構化資料）
    # ----------------------------------------------------------
    # dataset_id = 1234  # 換成你的資料集編號
    # records = [
    #     {
    #         "external_key": "faq-001",  # 選填：同一個主鍵再送一次會取代舊版，不會多一份
    #         "title": "標題1",
    #         "date": "2026-08-06",
    #         "content": "我是內容1",  # 必填
    #         "note1": "備註1",
    #         "note2": "備註2",
    #         "note3": "備註3",
    #     },
    #     {
    #         # 沒帶 external_key：單純新增，重送就會多一份
    #         "title": "標題2",
    #         "content": "我是內容2",
    #     },
    # ]
    # upload_records(dataset_id, records)
    # ----------------------------------------------------------

    # 主程式（資料上傳 - 上傳檔案）
    # ----------------------------------------------------------
    # dataset_id = 1234
    # upload_files(dataset_id, ["手冊.pdf", "說明.docx"], external_keys={"手冊.pdf": "manual-v1"})
    # Excel 每一列一筆：用 mapping 指定哪幾欄放進哪個欄位
    # upload_files(dataset_id, ["常見問題.xlsx"], mapping={"title": ["問題"], "content": ["答案"]})
    # ----------------------------------------------------------

    # 主程式（資料上傳 - 列出與刪除）
    # ----------------------------------------------------------
    # dataset_id = 1234
    # list_records(dataset_id)
    # delete_record(dataset_id, 101)  # 換成上傳時拿到的編號
    # delete_dataset(dataset_id)  # 刪除整個資料集，無法復原
    # ----------------------------------------------------------

    # 主程式（文字萃取 - Mode 1：只萃取國家）
    # ----------------------------------------------------------
    # extract_country_or_time("2024年3月15日，美國總統在白宮發表演說，討論與中國的貿易關係。", 1)
    # ----------------------------------------------------------

    # 主程式（文字萃取 - Mode 2：只萃取時間）
    # ----------------------------------------------------------
    # extract_country_or_time("明天下午3點將舉行記者會", 2, time_reference="2026-10-05 10:00:00")
    # ----------------------------------------------------------

    # 主程式（文字萃取 - Mode 3：同時萃取國家和時間）
    # ----------------------------------------------------------
    # extract_country_or_time("2024年3月15日，美國總統在白宮發表演說", 3)
    # ----------------------------------------------------------
