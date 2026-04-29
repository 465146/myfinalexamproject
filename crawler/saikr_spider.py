"""
赛氪网计算机竞赛爬虫
- 数据源：赛氪网公开 API (apiv4buffer.saikr.com)
- 爬取分类：程序设计(2)、计算机&信息技术(6)、大数据(34)、人工智能(1006)
- 文明爬取：请求间隔 2-3 秒
"""

import requests
import time
import json
import random
import os
from datetime import datetime

BASE_URL = "https://apiv4buffer.saikr.com/api/pc/contest/lists"
DETAIL_URL = "https://www.saikr.com/vse/{}"

# 计算机相关分类 ID
CS_CLASS_IDS = {
    2: "程序设计",
    6: "计算机&信息技术",
    34: "大数据",
    1006: "人工智能",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.saikr.com/contests",
}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def timestamp_to_str(ts):
    """Unix 时间戳转日期字符串"""
    if not ts or ts == 0:
        return ""
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return ""


def fetch_contest_list(class_id, page=1, limit=20, retries=3):
    """请求赛氪竞赛列表 API，带重试机制"""
    params = {
        "page": page,
        "limit": limit,
        "univs_id": "",
        "class_id": class_id,
        "level": 0,
        "sort": 0,
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 200:
                return data["data"]
            else:
                print(f"  [WARN] API 返回错误: code={data.get('code')}, msg={data.get('msg')}")
                return None
        except requests.RequestException as e:
            if attempt < retries:
                wait = random.uniform(3.0, 5.0) * attempt
                print(f"  [RETRY] 第 {attempt}/{retries} 次重试, 等待 {wait:.1f}s... ({e})")
                time.sleep(wait)
            else:
                print(f"  [ERROR] 请求失败 (已重试 {retries} 次): {e}")
                return None


def parse_contest(item, category_name):
    """解析单条竞赛数据"""
    return {
        "contest_id": item.get("contest_id"),
        "name": item.get("contest_name", "").strip(),
        "category": category_name,
        "level": item.get("level_name", ""),
        "organizer": item.get("organiser", ""),
        "scope": item.get("enter_range", ""),
        "regist_start": timestamp_to_str(item.get("regist_start_time")),
        "regist_end": timestamp_to_str(item.get("regist_end_time")),
        "contest_start": timestamp_to_str(item.get("contest_start_time")),
        "contest_end": timestamp_to_str(item.get("contest_end_time")),
        "status": item.get("time_name", ""),
        "url": DETAIL_URL.format(item.get("contest_id", "")),
        "source": "赛氪",
    }


def crawl_saikr(max_pages_per_category=5, limit=20):
    """
    爬取赛氪网计算机相关竞赛
    max_pages_per_category: 每个分类最多爬取页数
    limit: 每页条数
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_contests = []
    seen_ids = set()

    for class_id, class_name in CS_CLASS_IDS.items():
        print(f"\n{'='*60}")
        print(f"开始爬取分类: {class_name} (class_id={class_id})")
        print(f"{'='*60}")

        # 先请求第一页，获取总数
        first_page = fetch_contest_list(class_id, page=1, limit=limit)
        if not first_page:
            print(f"  [SKIP] 分类 {class_name} 第一页请求失败，跳过")
            continue

        total = first_page.get("total", 0)
        total_pages = (total + limit - 1) // limit
        actual_pages = min(total_pages, max_pages_per_category)

        print(f"  总记录数: {total}, 总页数: {total_pages}, 实际爬取: {actual_pages} 页")

        # 处理第一页数据
        for item in first_page.get("list", []):
            cid = item.get("contest_id")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                contest = parse_contest(item, class_name)
                all_contests.append(contest)
        print(f"  第 1 页完成, 累计: {len(all_contests)} 条")

        # 爬取后续页
        for page in range(2, actual_pages + 1):
            delay = random.uniform(2.0, 3.0)
            time.sleep(delay)

            result = fetch_contest_list(class_id, page=page, limit=limit)
            if not result or not result.get("list"):
                print(f"  第 {page} 页无数据，停止")
                break

            page_count = 0
            for item in result["list"]:
                cid = item.get("contest_id")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    contest = parse_contest(item, class_name)
                    all_contests.append(contest)
                    page_count += 1

            print(f"  第 {page} 页完成 (新增 {page_count} 条), 累计: {len(all_contests)} 条")

    # 保存结果
    output_file = os.path.join(OUTPUT_DIR, "saikr_cs_contests.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_contests, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"赛氪爬取完成!")
    print(f"  总计: {len(all_contests)} 条竞赛")
    print(f"  保存至: {output_file}")
    print(f"{'='*60}")

    return all_contests


if __name__ == "__main__":
    crawl_saikr(max_pages_per_category=5)
