# API 使用說明文件

## 目錄
- [0. 共通說明](#0-共通說明)
  - [網址](#網址)、[憑證](#憑證)、[請求格式](#請求格式)、[請求次數與額度](#請求次數與額度)、[回應錯誤處理](#回應錯誤處理)
- [1. 資料上傳 API](#1-資料上傳-api)
  - [與舊版對照](#與舊版對照)、[資料集編號](#資料集編號)
  - [1-1. 建立資料集](#1-1-建立資料集)：`POST /api/v1/datasets`
  - [1-2. 列出資料集](#1-2-列出資料集)：`GET /api/v1/datasets`
  - [1-3. 查詢單一資料集](#1-3-查詢單一資料集)：`GET /api/v1/datasets/{dataset_id}`
  - [1-4. 資料集改名](#1-4-資料集改名)：`PATCH /api/v1/datasets/{dataset_id}`
  - [1-5. 刪除資料集](#1-5-刪除資料集)：`DELETE /api/v1/datasets/{dataset_id}`
  - [1-6. 上傳結構化資料](#1-6-上傳結構化資料)：`POST /api/v1/datasets/{dataset_id}/records`
  - [1-7. 上傳檔案](#1-7-上傳檔案)：`POST /api/v1/datasets/{dataset_id}/files`
  - [1-8. 列出資料](#1-8-列出資料)：`GET /api/v1/datasets/{dataset_id}/records`
  - [1-9. 刪除一筆資料](#1-9-刪除一筆資料)：`DELETE /api/v1/datasets/{dataset_id}/records/{file_id}`
  - [資料處理狀態](#資料處理狀態)、[資料上傳錯誤列表](#資料上傳錯誤列表)、[注意事項](#注意事項)
- [2. 文字萃取 API（國家／時間）](#2-文字萃取-api國家時間)：`POST /api/extract/country-or-time`
  - [Mode 說明](#mode-說明)、[注意事項](#注意事項-1)

---

本文件說明外部程式以 API 金鑰（`X-API-Key`）呼叫的兩組 API：

| API | 用途 |
| --- | --- |
| [資料上傳 API](#1-資料上傳-api) | 建立資料集、上傳結構化資料或檔案、列出與刪除資料 |
| [文字萃取 API](#2-文字萃取-api國家時間) | 從一段文字萃取國家及／或時間 |

範例程式在 `sample.py`（Python），執行前先 `pip install -r requirements.txt`，再把檔案開頭的網址與 API 金鑰換成你自己的。

---

## 0. 共通說明

### 網址
所有 API 都打同一個網域，下文以 `https://<your-host>` 表示，請換成貴單位使用的網址。只支援 HTTPS。

### 憑證
每個請求都要帶 API 金鑰：

| KEY | VALUE |
| --- | --- |
| X-API-Key | 你的 API 金鑰（`sk_` 開頭） |

API 金鑰在後台「設定 → 萃取 API 金鑰」產生，只有租戶管理者能產生。**完整金鑰只在產生當下顯示一次**，之後只看得到末幾碼；重新產生後舊金鑰立即失效，請先把新金鑰換到所有呼叫的程式再重新產生。

> **API 金鑰只能從伺服器端呼叫**，不要寫進網頁前端程式。它是整個帳號共用的一把金鑰，拿到的人可以讀、改、刪帳號裡的所有資料集。

### 請求格式
| KEY | VALUE |
| --- | --- |
| Content-Type | `application/json`（只有上傳檔案那一支是 `multipart/form-data`） |

> 與舊版不同：憑證改放在標頭，不再放在 body 裡；body 直接送 JSON，不再包成 `jsonInputFile`、`extractCountryOrTimeVM` 這類表單欄位。
>
> body 必須是 UTF-8。在 Windows 命令列用 curl 送中文時，命令列可能不是用 UTF-8 送出，會收到 400「There was an error parsing the body」。請把 body 存成 UTF-8 檔案，改用 `--data-binary @body.json`。

### 請求次數與額度
| 項目 | 預設值 | 說明 |
| --- | --- | --- |
| API 金鑰的請求次數 | 每分鐘 120 次 | 資料上傳 API 與萃取 API **共用**；同一個來源 IP、同一個帳號各算一份，超過回 429 |
| 萃取次數 | 每日 100 次 | 每呼叫一次萃取 API 扣一次；**萃取不到或失敗也照扣** |
| 儲存空間 | 100 MB | 上傳的資料與檔案佔用的空間 |

以上是新帳號的預設值，實際數字以貴帳號的方案為準。每日額度以台北時間換日。

### 回應錯誤處理
每個回應都帶 `X-Correlation-ID` 標頭（關聯編號），回報問題時請一併提供。

錯誤訊息的語言跟著帳號的介面語言（繁體中文或英文）；金鑰錯誤這類還認不出帳號的錯誤，一律是繁體中文。

#### 錯誤格式
錯誤回應有以下幾種形狀，建議先看 HTTP 狀態碼，需要細分時再看 `code`：

| 形狀 | 範例 |
| --- | --- |
| 只有訊息 | `{"detail": "缺少或無效的 API 金鑰（X-API-Key）"}` |
| 錯誤代碼在 `detail` 裡 | `{"detail": {"code": "rate_limited", "detail": "請求過於頻繁，請稍後再試"}}` |
| 錯誤代碼在最外層 | `{"code": "upload_too_large", "detail": "本次請求內容超過上限 4 MB"}`<br>`{"error": "萃取次數不足", "code": "extraction_exceeded"}` |
| 欄位驗證失敗（422） | `{"detail": [{"type": "missing", "loc": ["body", "name"], "msg": "Field required"}]}` |

#### 共通錯誤列表
| HTTP | Code | Message | 說明 |
| --- | --- | --- | --- |
| 401 | | `{"error": "no api key"}` | 完全沒帶 `X-API-Key` |
| 401 | | 缺少或無效的 API 金鑰（X-API-Key） | API 金鑰錯誤或已被重新產生 |
| 403 | account_frozen | （無訊息） | 帳號已被凍結 |
| 403 | disclaimer_required | （無訊息） | 帳號尚未啟用，管理者需要先登入後台接受免責聲明 |
| 403 | subscription_expired | （無訊息） | 使用期已到期 |
| 403 | tenant_feature_disabled | 這個租戶沒有開通「data」功能 | 帳號沒有開通這項功能，`cap` 欄位會寫是哪一項：`data`（資料上傳）、`extract`（萃取） |
| 413 | upload_too_large | 本次請求內容超過上限 4 MB | JSON body 超過 4 MB |
| 422 | | （見上方欄位驗證失敗的形狀） | 欄位缺漏、型別錯誤、超出長度 |
| 429 | rate_limited | 請求過於頻繁，請稍後再試 | 超過每分鐘請求次數。回應帶 `Retry-After`（秒），等待後重試 |
| 502 | | `{"error": "upstream unreachable"}` | 服務暫時連不上，請稍後重試 |
| 503 | database_unavailable | 資料庫目前無法連線，請稍後再試 | 回應帶 `Retry-After: 5` |

---

## 1. 資料上傳 API

### 與舊版對照
| 舊版 | 新版 |
| --- | --- |
| `JsonUploadInputApi`，`Action=0` 新增 | `POST /api/v1/datasets/{dataset_id}/records`，一筆資料就是一份文件 |
| `JsonUploadInputApi`，`Action=2` 用 `FileName` 刪除 | `DELETE /api/v1/datasets/{dataset_id}/records/{file_id}`，用上傳時拿到的編號刪除 |
| 同一份資料要更新：先刪再新增 | 帶 `external_key`，會直接取代舊版 |
| `ApiKey`（放在 body） | `X-API-Key` 標頭 |
| `FolderSn`（原始資料集編號） | 網址裡的 `{dataset_id}` |
| `FieldTitle`／`FieldTime`／`FieldContent` | `title`／`date`／`content` |
| `CusField`（固定三個字串） | `note1`～`note10`（要用幾個就填幾個） |
| 只能送 JSON 資料 | 另外可以直接上傳 pdf／docx／xlsx 檔案；也可以用 API 建立、改名、刪除資料集 |

### 資料集編號
資料集編號（`dataset_id`）可以從[列出資料集](#1-2-列出資料集)取得，也可以在後台打開資料集頁時從網址列看到，例如 `https://<your-host>/datasets/12` 的 `12`。

---

### 1-1. 建立資料集

#### URL
Post https://&lt;your-host&gt;/api/v1/datasets

#### 請求資料範例
##### Layer 1
| KEY | VALUE |
| --- | --- |
| body | json 格式，範例 |
| | { |
| | "name": "產品手冊", |
| | "description": "各型號產品的規格與保固說明" |
| | } |

##### Layer 2
| KEY | VALUE |
| --- | --- |
| name | 資料集名稱，必填，同一個帳號裡不能重複 |
| description | 資料集描述，選填。問答時會用它判斷問題該查哪一個資料集，建議寫清楚這個資料集裝的是什麼。**建立後無法用 API 修改** |

#### curl 請求範例
```bash
curl -X POST "https://<your-host>/api/v1/datasets" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"name":"產品手冊","description":"各型號產品的規格與保固說明"}'
```
記得換掉 your_api_key

#### 回應資料範例
成功回 HTTP 201：
```json
{"id": 12, "index_name": "t3_1a2b3c4d", "name": "產品手冊"}
```

| KEY | VALUE |
| --- | --- |
| id | 資料集編號，之後上傳資料時要用，**建議存起來** |
| index_name | 系統內部的索引名稱 |
| name | 資料集名稱 |

> 新的資料集會自動加入後台「對話設定」，裡面的資料上傳並處理完成後（見[資料處理狀態](#資料處理狀態)）就能被問答查到。

#### 回應錯誤處理
| HTTP | Message | 說明 |
| --- | --- | --- |
| 400 | 資料集名稱不可為空 | `name` 是空的或只有空白 |
| 409 | 資料集名稱已存在 | 名稱重複 |
| 502 | GufoRAG 呼叫失敗（建立索引「…」）。請提供關聯編號 … 給維運人員查詢詳情。 | 建立失敗，沒有留下資料集，可以重試 |

---

### 1-2. 列出資料集

#### URL
Get https://&lt;your-host&gt;/api/v1/datasets

#### curl 請求範例
```bash
curl "https://<your-host>/api/v1/datasets" -H "X-API-Key: your_api_key"
```

#### 回應資料範例
```json
[
  {"id": 12, "name": "產品手冊", "index_name": "t3_1a2b3c4d", "group_id": null, "file_count": 3}
]
```

| KEY | VALUE |
| --- | --- |
| id | 資料集編號 |
| name | 資料集名稱 |
| index_name | 系統內部的索引名稱 |
| group_id | 所屬群組；用 API 建立的資料集是 `null` |
| file_count | 資料集裡有幾份資料或檔案 |

> 清單包含帳號裡所有資料集，也包含後台建立的 QA 集。QA 集不能用這組 API 上傳資料（會回 409 `use_qa_import`）。

---

### 1-3. 查詢單一資料集

#### URL
Get https://&lt;your-host&gt;/api/v1/datasets/{dataset_id}

回應欄位與[列出資料集](#1-2-列出資料集)的單筆相同。資料集不存在時回 404「找不到這個資料集」。

---

### 1-4. 資料集改名

#### URL
Patch https://&lt;your-host&gt;/api/v1/datasets/{dataset_id}

#### 請求資料範例
```json
{"name": "產品手冊（新版）"}
```

#### curl 請求範例
```bash
curl -X PATCH "https://<your-host>/api/v1/datasets/12" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"name":"產品手冊（新版）"}'
```

#### 回應資料範例
回應欄位與[列出資料集](#1-2-列出資料集)的單筆相同。

#### 回應錯誤處理
| HTTP | Message | 說明 |
| --- | --- | --- |
| 400 | 資料集名稱不可為空 | |
| 404 | 找不到這個資料集 | |
| 409 | 資料集名稱已存在 | |

---

### 1-5. 刪除資料集
刪除整個資料集與裡面所有資料。**無法復原。**

#### URL
Delete https://&lt;your-host&gt;/api/v1/datasets/{dataset_id}

#### curl 請求範例
```bash
curl -X DELETE "https://<your-host>/api/v1/datasets/12" -H "X-API-Key: your_api_key"
```

#### 回應資料範例
```json
{"deleted": 12}
```

#### 回應錯誤處理
| HTTP | Message | 說明 |
| --- | --- | --- |
| 404 | 找不到這個資料集 | |
| 502 | 移除資料集失敗（index=…）。請提供關聯編號 … 給維運人員查詢詳情。 | 刪除失敗，資料集仍在，可以重試 |

> API 金鑰可以刪除帳號裡的任何資料集，包括後台建立的，請小心使用。

---

### 1-6. 上傳結構化資料
上傳一批資料，**每一筆資料會成為一份文件**。對應舊版的 `JsonUploadInputApi` 新增。

#### URL
Post https://&lt;your-host&gt;/api/v1/datasets/{dataset_id}/records

#### 請求資料範例
##### Layer 1
| KEY | VALUE |
| --- | --- |
| body | json 格式，範例 |
| | { |
| | "records": [{"external_key": "faq-001", "title": "退貨規定", "date": "2026-08-06", "content": "商品到貨七天內可申請退貨。", "category": "售後服務", "note1": "備註1"}], |
| | "convert_html": true |
| | } |

##### Layer 2
| KEY | VALUE |
| --- | --- |
| records | 要上傳的資料陣列，每一筆是一個物件（欄位見 Layer 3）。整個 body 不能超過 4 MB，資料量大時請分批送，建議一批幾千筆以內 |
| convert_html | `content` 是否從 HTML 轉成 Markdown，選填，預設 `true`。內容要逐字保留時填 `false` |

##### Layer 3（records 每一筆）
| KEY | VALUE |
| --- | --- |
| content | 內容欄位，**必填**，不能是空白。問答主要就是查這一欄 |
| title | 標題欄位，同時會當作這份資料在後台顯示的名稱（沒填則顯示「記錄1」「記錄2」…） |
| date | 日期欄位，格式見下方「日期格式」，可以用來篩選 |
| source | 來源欄位 |
| category | 分類欄位，可以用來篩選 |
| number | 數值欄位，請填數字，可以用來篩選 |
| flag | 是非欄位，請填 `true` 或 `false`，可以用來篩選 |
| tags | 標籤欄位，填逗號分隔的整數，例如 `"1,2,3"` |
| note1～note10 | 自訂文字欄位。若管理者在後台「標籤維度與檢索過濾」替這一欄設定了標籤字典，值必須是字典裡的代碼 |
| date2、date3 | 自訂日期欄位，格式同 `date`，沒寫時區時當作 UTC |
| internal_note | 內部註記，只存在後台，**不會被問答查到** |
| external_key | （選填）你這一側的資料主鍵，見下方說明。它不會出現在文件內容裡 |

> 只有 `content` 必填，其他欄位用不到就不要帶，或填 `null`；空字串會被當作沒填。欄位名稱要完全一樣（大小寫有別），打錯會在該筆回 `unknown_slot`。每一個欄位最多 32,767 字。

##### 日期格式
| 可以 | 不可以 |
| --- | --- |
| `2026-12-31`、`2026/12/31`、`2026.12.31`、`2026-1-5`、`20261231` | 年在後：`31/12/2026` |
| 後面接時間：`2026-12-31 10:00:00`、`2026-12-31T10:00:00+08:00` | 分隔符號混用：`2026-12/31` |
| `null` 或空字串（代表沒有日期） | 不存在的日期：`2026-02-30` |

##### external_key 說明
- 帶了 `external_key` 的資料，代表「這一份資料的最新版」：同一個資料集裡已經有同一個 `external_key` 的舊資料時，**舊資料會被取代**，不會多一份。
- 不帶就是單純新增；同一份資料送兩次就會有兩份。
- 需要重送或定期更新的資料，**強烈建議都帶 `external_key`**。
- 同一次請求裡不能有兩筆用同一個 `external_key`（前後空白不計），否則整個請求回 400。

#### curl 請求範例
```bash
curl -X POST "https://<your-host>/api/v1/datasets/12/records" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"records":[{"external_key":"faq-001","title":"退貨規定","date":"2026-08-06","content":"商品到貨七天內可申請退貨。"}]}'
```
記得換掉 your_api_key 與資料集編號

#### 回應資料範例
**每一筆資料各自成功或失敗**，有幾筆失敗不影響其他筆，HTTP 仍是 200，請逐筆檢查 `results`。

##### Layer 1
| KEY | VALUE |
| --- | --- |
| body | json 格式，範例 |
| | { |
| | "imported": 1, |
| | "inserted": 1, |
| | "updated": 0, |
| | "failed": 1, |
| | "results": [ |
| | {"ok": true, "doc": 101, "updated": false, "replaced_file_id": null, "task_id": "8c1f...", "sync_state": {"state": "pending", "indexed_count": null, "failed_count": null, "reason": null}}, |
| | {"ok": false, "error": "content 欄位不可為空", "code": "content_required"} |
| | ], |
| | "health_scan": {"ok": true, "detail": null, "scan": {...}} |
| | } |

##### Layer 2
| KEY | VALUE |
| --- | --- |
| imported | 成功筆數（= inserted + updated） |
| inserted | 新增的筆數 |
| updated | 用 `external_key` 取代舊資料的筆數 |
| failed | 失敗的筆數 |
| results | 每一筆的結果，**順序與送出的 `records` 相同**，見 Layer 3 |
| health_scan | 上傳後系統自動做的資料檢查結果，僅供參考；`ok` 為 `false` 不影響這次上傳 |

##### Layer 3（results 每一筆）
| KEY | VALUE |
| --- | --- |
| ok | 這一筆是否成功 |
| doc | 這一筆在系統裡的編號，之後要刪除時用，**建議存起來** |
| updated | 這一筆是否取代了舊資料 |
| replaced_file_id | 被取代的舊資料編號，沒有則是 `null` |
| task_id | 系統內部的處理編號 |
| sync_state | 處理狀態，見 [資料處理狀態](#資料處理狀態) |
| error | 失敗原因（失敗時才有） |
| code | 錯誤代碼（失敗時才有），見 [資料上傳錯誤列表](#資料上傳錯誤列表) |
| unfilterable_empty_slots | 提示用：`date`、`category`、`number`、`flag` 這幾個篩選欄位中，這一筆沒填的那幾個，這一筆因此無法用它們篩選。不是錯誤 |
| dropped_links、unprocessable_tables | HTML 轉換時被拿掉的連結、無法轉換的表格（有才出現） |

---

### 1-7. 上傳檔案
直接上傳 pdf／docx／xlsx 檔案，一次可以傳多個。

#### URL
Post https://&lt;your-host&gt;/api/v1/datasets/{dataset_id}/files

#### 請求格式
| KEY | VALUE |
| --- | --- |
| Content-Type | multipart/form-data |
| X-API-Key | 你的 API 金鑰 |

#### 請求資料範例
| KEY | VALUE |
| --- | --- |
| files | 要上傳的檔案，可以重複帶多個。支援 `.pdf`、`.docx`、`.xlsx`；一次最多 200 個，單檔最大 50 MB，全部合計最大 200 MB |
| mapping | （選填，只對 xlsx 有效）json 字串，指定哪幾欄要放進哪個欄位，例如 `{"content": ["答案"], "title": ["問題"]}`。欄位名稱同 [1-6 Layer 3](#layer-3records-每一筆)，值是 xlsx 的欄名陣列，`content` 必填 |
| external_keys | （選填）json 字串，每個檔案的 `external_key`，例如 `{"手冊.pdf": "manual-v1"}`，鍵是檔名 |
| convert_html | （選填）是否把 HTML 轉成 Markdown，預設 `true` |
| header_rows | （選填）xlsx 的表頭佔幾列，1～10，預設 1。大於 1 時 `mapping` 的欄名要用全形斜線串起來，例如 `"常見問題／問題"` |
| unpivot | （選填）xlsx 是交叉表時填 `true`，會攤平成一列一筆。這時 `mapping` 的欄名只能用 `"列標題"`、`"欄標題"`、`"值"` |
| unpivot_row_label_cols | （選填）交叉表的列標題在第幾欄，從 1 起算，可以重複帶多個，預設 1 |

##### 不同檔案怎麼處理
| 檔案 | 處理方式 |
| --- | --- |
| pdf、docx | 抽出全文放進 `content`，整份成為一份文件 |
| xlsx，有帶 `mapping` | 只讀第一張工作表，**每一列成為一份文件**（與後台的 Excel 匯入相同） |
| xlsx，沒帶 `mapping` | 整份成為一份文件，不分欄位；這種檔案不能帶 `external_key` |

#### curl 請求範例
上傳兩份文件：
```bash
curl -X POST "https://<your-host>/api/v1/datasets/12/files" \
  -H "X-API-Key: your_api_key" \
  -F "files=@手冊.pdf" \
  -F "files=@說明.docx" \
  -F 'external_keys={"手冊.pdf":"manual-v1"}'
```

上傳 Excel，每一列一筆：
```bash
curl -X POST "https://<your-host>/api/v1/datasets/12/files" \
  -H "X-API-Key: your_api_key" \
  -F "files=@常見問題.xlsx" \
  -F 'mapping={"title":["問題"],"content":["答案"],"category":["分類"]}'
```
記得換掉 your_api_key 與資料集編號

#### 回應資料範例
與 1-6 相同，**每一個檔案各自成功或失敗**，請逐筆檢查 `results`。

```json
{
  "inserted": 2,
  "updated": 0,
  "failed": 1,
  "results": [
    {"filename": "手冊.pdf", "ok": true, "file_id": 11, "updated": false, "replaced_file_id": null,
     "task_id": "…", "sync_state": {"state": "pending", "indexed_count": null, "failed_count": null, "reason": null},
     "structure": {"pages": 12, "tables": 1, "table_rows": 8, "continuation_tables": 0, "suspected_table_pages": 0}},
    {"filename": "常見問題.xlsx", "ok": true, "file_id": 12, "connector": "excel", "data_count": 250, "updated": false,
     "replaced_file_id": null, "task_id": "…", "sync_state": {"state": "pending", "indexed_count": null, "failed_count": null, "reason": null}},
    {"filename": "忽略.txt", "ok": false, "error": "僅支援 .pdf / .docx / .xlsx"}
  ],
  "health_scan": {"ok": true, "detail": null, "scan": {}}
}
```

| KEY | VALUE |
| --- | --- |
| filename | 檔名，用來對應是哪一個檔案 |
| file_id | 這個檔案在系統裡的編號，之後要刪除時用，**建議存起來** |
| connector | xlsx 才有：`excel`＝有帶 mapping，每列一筆；`folder`＝沒帶 mapping，整份一筆 |
| data_count | 有帶 mapping 的 xlsx 才有：送出的資料列數 |
| structure | pdf／docx 才有：頁數、段落數、表格數等，供確認內容有沒有完整抽出 |
| 其他欄位 | 同 1-6 Layer 3 |

> 回應裡沒有 `imported`，成功數請用 `inserted + updated`。

---

### 1-8. 列出資料
列出資料集裡的每一份資料與檔案。

#### URL
Get https://&lt;your-host&gt;/api/v1/datasets/{dataset_id}/records

#### curl 請求範例
```bash
curl "https://<your-host>/api/v1/datasets/12/records" -H "X-API-Key: your_api_key"
```

#### 回應資料範例
```json
{
  "dataset_id": 12,
  "files": [
    {"id": 101, "filename": "退貨規定", "file_type": "api", "connector_type": "excel",
     "size_bytes": 4877, "uploaded_at": "2026-10-05T03:12:45.123456Z", "record_count": 1}
  ]
}
```

| KEY | VALUE |
| --- | --- |
| id | 編號，就是上傳時拿到的 `doc` 或 `file_id` |
| filename | 名稱：結構化資料是 `title`（或「記錄N」），檔案是原始檔名 |
| file_type | `api`＝結構化資料、`pdf`、`word`、`xlsx` |
| connector_type | `excel` 或 `folder`（沒帶 mapping 的 xlsx） |
| size_bytes | 佔用的儲存空間（位元組） |
| uploaded_at | 上傳時間（UTC） |
| record_count | 包含幾筆資料；查不到時是 `null` |

依上傳時間由新到舊排列。

> 回應裡沒有 `external_key` 與資料內容，`external_key` 與編號的對應請自己保存。

---

### 1-9. 刪除一筆資料
刪除一份資料或一個檔案。對應舊版 `JsonUploadInputApi` 的刪除。

#### URL
Delete https://&lt;your-host&gt;/api/v1/datasets/{dataset_id}/records/{file_id}

`{file_id}` 換成上傳時拿到的 `doc`／`file_id`，或[列出資料](#1-8-列出資料)的 `id`。

#### curl 請求範例
```bash
curl -X DELETE "https://<your-host>/api/v1/datasets/12/records/101" -H "X-API-Key: your_api_key"
```

#### 回應資料範例
```json
{"deleted": 101}
```

> 有帶 mapping 的 xlsx 是一個檔案一個編號，刪除它會刪掉那個檔案的所有列。

#### 回應錯誤處理
| HTTP | Code | Message | 說明 |
| --- | --- | --- | --- |
| 404 | | 找不到這個資料集 | |
| 404 | | 找不到這個檔案 | 編號不在這個資料集裡 |
| 502 | | 從 GufoRAG 移除…失敗…。請提供關聯編號 … | 刪除失敗，資料仍在，可以重試 |

---

### 資料處理狀態
上傳 API 回應時，資料已經存進系統並開始建立索引，但**建立索引是在背景進行的**，回應回來時多半還沒完成，資料可能要再等一下才能被問答查到。`sync_state` 告訴你送出當下的狀況：

| state | 說明 |
| --- | --- |
| pending | 還在處理中（最常見）。不代表成功，也不代表失敗 |
| succeeded | 已處理完成，沒有任何失敗 |
| failed | 處理失敗（部分失敗也算），`reason` 有說明與關聯編號 |
| unknown | 資料已送出，但查不到處理結果。**請先不要重送同一份資料**，把 `reason` 裡的關聯編號提供給我們確認 |

| KEY | VALUE |
| --- | --- |
| indexed_count | 已建立索引的文件數；`null` 代表還不知道（不等於 0） |
| failed_count | 失敗的文件數；`null` 代表還不知道 |
| reason | `failed`／`unknown` 時的說明 |

> 目前沒有事後查詢處理狀態的 API。資料需要重送時請帶 `external_key`，重送只會取代舊版，不會多出一份。

---

### 資料上傳錯誤列表
#### 整個請求失敗
| HTTP | Code | Message | 說明 |
| --- | --- | --- | --- |
| 400 | duplicate_external_key | 同一次請求裡「第 1 筆」與「第 2 筆」共用外部主鍵「K1」… | 同一次請求有重複的 `external_key` |
| 400 | bad_external_key | external_key 不可為空字串… | `external_key` 是空字串，不需要時請整個不要帶 |
| 400 | bad_external_keys | external_keys 必須是合法 JSON… | 上傳檔案時 `external_keys` 格式錯誤 |
| 400 | bad_mapping | mapping 必須是合法 JSON… | 上傳檔案時 `mapping` 格式錯誤 |
| 400 | too_many_import_files | 這次上傳的檔案有 201 筆，超過上限 200… | 一次超過 200 個檔案 |
| 404 | | 找不到這個資料集 | `dataset_id` 錯誤 |
| 409 | use_qa_import | 這是 QA 集，請用 QA 匯入… | 目標是 QA 集，不能用這組 API 上傳 |
| 413 | upload_too_large | 檔案「x.pdf」超過上限 50 MB | 單檔超過 50 MB，或合計超過 200 MB。**排在前面、已經處理完的檔案仍會存進去** |

#### 單筆失敗（寫在 results 裡，HTTP 仍是 200）
| Code | Message | 說明 |
| --- | --- | --- |
| content_required | content 欄位不可為空 | 沒有 `content`，或只有空白 |
| unknown_slot | 未知的欄位槽：… | 欄位名稱打錯 |
| bad_external_key | external_key 必須是字串 | |
| bad_date_slot | 日期欄位槽的值不是合法的日期：… | 日期格式錯誤，見[日期格式](#日期格式) |
| date_out_of_filterable_range | | 日期超出 1677～2262 年 |
| bad_int_array_slot | | `tags` 不是逗號分隔的整數 |
| unknown_tag_code | | 值不在這一欄的標籤字典裡 |
| content_empty_after_conversion | 內容經 HTML 轉換後不剩任何文字… | 內容要逐字保留時請帶 `convert_html=false` |
| storage_exceeded | 儲存空間不足 | 帳號儲存空間用完，另外帶 `used_mb`、`limit_mb` |
| unknown_column | | xlsx 找不到 `mapping` 指定的欄名 |
| content_cell_required | | xlsx 有幾列的 `content` 是空的，`rows` 會列出是哪幾列 |
| external_key_unsupported | | 沒帶 mapping 的 xlsx 不能帶 `external_key` |
| （無） | 僅支援 .pdf / .docx / .xlsx | 不支援的檔案類型 |
| （無） | 無法解析 PDF 檔案：…／這個 PDF 有密碼保護… | 檔案損毀或加密 |
| （無） | 處理失敗。請提供關聯編號 … 給維運人員查詢詳情。 | 其他錯誤，請提供關聯編號給我們 |

### 注意事項
1. 每一個欄位最多 32,767 字。**pdf／docx 抽出的全文也算一個欄位**，約 50 頁以上的中文文件可能超過而失敗，請先分割檔案。
2. 掃描成圖片的 pdf 抽不到文字，仍會回成功，但內容是空的。
3. 用 API 建立的資料集，在後台只有租戶管理者能修改或刪除。
4. 上傳時是逐筆處理，資料量大時回應會比較久，請把 HTTP 用戶端的逾時設長一點。

---

## 2. 文字萃取 API（國家／時間）
從一段文字中萃取國家及／或時間。對應舊版的 `JsonUploadInputApi/ExtractCountryOrTime`。

### URL
Post https://&lt;your-host&gt;/api/extract/country-or-time

### 請求格式
| KEY | VALUE |
| --- | --- |
| Content-Type | application/json |
| X-API-Key | 你的 API 金鑰 |

### 請求資料範例
#### Layer 1
| KEY | VALUE |
| --- | --- |
| body | json 格式，範例 |
| | { |
| | "text": "2024年3月15日，美國總統在白宮發表演說", |
| | "mode": 3, |
| | "time_reference": "2024-03-15 10:00:00" |
| | } |

#### Layer 2
| KEY | 必填 | VALUE |
| --- | --- | --- |
| text | 是 | 要分析的文字，去掉頭尾空白後 2～5000 字 |
| mode | 是 | 萃取模式，**數字** `1`、`2` 或 `3`（舊版是字串） |
| time_reference | 否 | 發文時間參考，最多 200 字。提供的話可以更準確地判斷「明天」「下週三」這類相對時間 |

### Mode 說明
| Mode | 功能說明 | 回傳內容 |
| --- | --- | --- |
| 1 | 只萃取國家 | country（國家或「無」）<br>time 為 null |
| 2 | 只萃取時間 | time（時間或「無」）<br>country 為 null |
| 3 | 同時萃取國家和時間 | country（國家或「無」）<br>time（時間或「無」） |

### curl 請求範例
```bash
curl -X POST "https://<your-host>/api/extract/country-or-time" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"text":"2024年3月15日，美國總統在白宮發表演說","mode":3,"time_reference":"2024-03-15 10:00:00"}'
```
記得換掉 your_api_key

### 回應資料範例
#### 成功回應格式
```json
{"country": "美國", "time": "2024-03-15 00:00:00"}
```

> 與舊版不同：結果直接放在最外層，不再包在 `JsonData` 字串裡；欄位名稱改成小寫 `country`、`time`。

#### 回應內容說明
| KEY | VALUE |
| --- | --- |
| country | 萃取到的國家名稱，或「無」（mode 為 2 時是 null） |
| time | 萃取到的時間，格式 `yyyy-MM-dd HH:mm:ss`，或「無」（mode 為 1 時是 null）。只有年或月時，會取該月 2 日，例如 `2000-01-02 00:00:00` |

#### 回傳範例說明
1. **Mode = 1（只萃取國家）**
   ```json
   {"country": "美國", "time": null}
   ```
2. **Mode = 2（只萃取時間）**
   ```json
   {"country": null, "time": "2024-03-15 00:00:00"}
   ```
3. **Mode = 3（同時萃取）**
   ```json
   {"country": "美國", "time": "2024-03-15 00:00:00"}
   ```
4. **沒有找到資訊時**
   ```json
   {"country": "無", "time": "無"}
   ```

### 回應錯誤處理
除了[共通錯誤](#共通錯誤列表)，還可能出現：

| HTTP | Code | Message | 說明 |
| --- | --- | --- | --- |
| 400 | | text 長度必須在 2 到 5000 字之間 | |
| 400 | | mode 必須為 1(國家)/2(時間)/3(兩者) | |
| 400 | | time_reference 為 201 字，超過上限 200… | |
| 429 | extraction_exceeded | 萃取次數不足 | 本期萃取次數用完，回應是 `{"error": "萃取次數不足", "code": "extraction_exceeded"}`，**沒有 `Retry-After`** |
| 503 | | 萃取服務未設定（缺 OPENAI_API_KEY） | 服務端尚未設定，請聯絡我們 |
| 500 | | `Internal Server Error`（純文字） | 萃取過程失敗，請稍後重試 |

### 注意事項
1. `text` 長度是去掉頭尾空白後計算，必須在 2～5000 字之間。
2. `mode` 必須是數字 1、2 或 3。
3. `time_reference` 為選填，提供發文時間可以更準確地判斷相對時間。
4. 若萃取不到資訊，會回傳「無」而不是 null（在該 mode 需要回傳的欄位中）。
5. 時間格式不保證完全符合 `yyyy-MM-dd HH:mm:ss`，請在程式裡做好解析失敗的處理。
6. 每次呼叫會消耗一次萃取次數，**萃取不到或失敗也照扣**，請注意額度。
