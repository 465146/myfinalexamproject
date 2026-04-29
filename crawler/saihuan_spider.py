"""
赛欢网科技竞赛爬虫
- 数据源：赛欢网 (saihuan.net) 静态 HTML
- 爬取分类：科技竞赛
- 文明爬取：请求间隔 2-3 秒
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import random
import os
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

BASE_URL = "https://www.saihuan.net"
LIST_URL = "https://www.saihuan.net/article/keji.html"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# 计算机相关关键词
CS_KEYWORDS = [
    "计算机", "程序", "编程", "算法", "软件", "人工智能", "AI", "大数据",
    "机器学习", "深度学习", "网络安全", "信息安全", "数据结构", "操作系统",
    "数据库", "云计算", "物联网", "嵌入式", "区块链", "数字化", "智能",
    "ACM", "ICPC", "CCPC", "蓝桥杯", "天梯赛", "代码", "开发", "Web",
    "电子设计", "机器人", "自动化", "信息", "网络", "C4", "AIGC",
    "芯片", "半导体", "电路", "信号", "通信", "5G",
]


def is_cs_related(text):
    """判断是否与计算机相关"""
    return any(kw in text for kw in CS_KEYWORDS)


def normalize_url(href):
    """将相对 URL 转为绝对 URL"""
    if href.startswith("/"):
        return BASE_URL + href
    elif not href.startswith("http"):
        return BASE_URL + "/" + href
    return href


def parse_competition_items(soup):
    """从页面解析竞赛条目 - 基于 competition-item 结构"""
    contests = []

    # 模式1: .competition-item 容器
    items = soup.find_all("div", class_=re.compile(r"competition|contest|item|post", re.I))
    if not items:
        # 模式2: article 标签
        items = soup.find_all("article")

    for item in items:
        # 提取标题和链接
        title_tag = item.find(["h2", "h3", "h4"], class_=re.compile(r"title|name", re.I))
        if not title_tag:
            title_tag = item.find(["h2", "h3", "h4"])

        if not title_tag:
            continue

        a_tag = title_tag.find("a", href=True)
        if not a_tag:
            continue

        name = a_tag.get_text(strip=True)
        url = normalize_url(a_tag["href"])

        if not name or len(name) < 4:
            continue

        contest = {"name": name, "url": url, "source": "赛欢网"}

        # 提取标签
        tags = item.find_all("span", class_=re.compile(r"tag", re.I))
        if tags:
            contest["tags"] = ", ".join(t.get_text(strip=True) for t in tags if t.get_text(strip=True))

        # 提取日期
        date_tag = item.find("span", class_=re.compile(r"date|time", re.I))
        if date_tag:
            contest["date"] = date_tag.get_text(strip=True)

        # 提取描述
        desc_tag = item.find("div", class_=re.compile(r"desc|summary|excerpt", re.I))
        if desc_tag:
            contest["description"] = desc_tag.get_text(strip=True)[:500]

        # 提取浏览量
        views_tag = item.find("span", class_=re.compile(r"view|read", re.I))
        if views_tag:
            contest["views"] = views_tag.get_text(strip=True)

        contests.append(contest)

    return contests


def parse_sidebar_events(soup):
    """从侧边栏推荐区域提取赛事"""
    contests = []

    # 侧边栏推荐赛事
    for section in soup.find_all("div", class_=re.compile(r"section|sidebar|widget", re.I)):
        section_title = section.find(["h3", "h4"], class_=re.compile(r"title", re.I))
        if not section_title:
            continue
        title_text = section_title.get_text(strip=True)
        if "赛事" not in title_text and "喜欢" not in title_text:
            continue

        for li in section.find_all("li"):
            a = li.find("a", href=True)
            if not a:
                continue
            name = a.get_text(strip=True)
            url = normalize_url(a["href"])
            if name and len(name) > 5:
                contest = {"name": name, "url": url, "source": "赛欢网"}
                date_span = li.find("span", class_=re.compile(r"date", re.I))
                if date_span:
                    contest["date"] = date_span.get_text(strip=True)
                contests.append(contest)

    return contests


def fetch_detail_page(url):
    """爬取竞赛详情页"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        detail = {}

        # 提取正文
        content_area = (
            soup.find("div", class_=re.compile(r"content|article|entry|post|detail", re.I))
            or soup.find("article")
            or soup.find("main")
        )

        if content_area:
            text = content_area.get_text(separator="\n", strip=True)
            detail["description"] = text[:3000]

            for line in text.split("\n"):
                line = line.strip()
                if "主办" in line and "：" in line:
                    detail["organizer"] = line.split("：", 1)[-1].strip()
                elif "报名" in line and "时间" in line and "：" in line:
                    detail["regist_time"] = line.split("：", 1)[-1].strip()
                elif "比赛" in line and "时间" in line and "：" in line:
                    detail["contest_time"] = line.split("：", 1)[-1].strip()
                elif "级别" in line and "：" in line:
                    detail["level"] = line.split("：", 1)[-1].strip()
                elif "参赛对象" in line and "：" in line:
                    detail["participants"] = line.split("：", 1)[-1].strip()

        return detail

    except requests.RequestException as e:
        print(f"    [ERROR] 详情页请求失败 {url}: {e}")
        return {}


def crawl_saihuan(max_pages=5, fetch_details=True):
    """
    爬取赛欢网科技竞赛
    max_pages: 最多翻页数（AJAX加载更多的情况，尝试多次翻页）
    fetch_details: 是否爬取详情页
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"开始爬取赛欢网科技竞赛")
    print(f"列表页: {LIST_URL}")
    print(f"{'='*60}")

    # 爬取列表页
    try:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] 列表页请求失败: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # 解析主列表区
    all_contests = []
    seen_urls = set()

    main_items = parse_competition_items(soup)
    sidebar_items = parse_sidebar_events(soup)

    # 合并并过滤
    for c in main_items + sidebar_items:
        if c["url"] not in seen_urls and is_cs_related(c.get("name", "")):
            seen_urls.add(c["url"])
            all_contests.append(c)

    print(f"  列表页解析: 主区 {len(main_items)} 条, 侧边栏 {len(sidebar_items)} 条")
    print(f"  计算机相关: {len(all_contests)} 条")

    # 尝试 AJAX 加载更多 (赛欢网使用 load-more 按钮)
    # 分析页面 JS 找到 AJAX 接口
    ajax_url = None
    for script in soup.find_all("script"):
        if script.string and ("loadmore" in script.string.lower() or "ajax" in script.string.lower()):
            # 尝试提取 AJAX URL
            match = re.search(r'url\s*[=:]\s*["\']([^"\']+)["\']', script.string)
            if match:
                ajax_url = match.group(1)
                if ajax_url.startswith("/"):
                    ajax_url = BASE_URL + ajax_url
                print(f"  发现 AJAX 加载接口: {ajax_url}")
                break

    # 如果没找到 AJAX 接口，尝试常见的 WordPress AJAX 模式
    if not ajax_url:
        # 赛欢网可能使用 WordPress 的 admin-ajax.php
        ajax_url = BASE_URL + "/wp-admin/admin-ajax.php"
        print(f"  尝试 WordPress AJAX 接口: {ajax_url}")

    if ajax_url:
        for page in range(2, max_pages + 1):
            try:
                # 尝试 POST 请求加载更多
                data = {
                    "action": "loadmore",
                    "page": page,
                    "category": "keji",
                }
                time.sleep(random.uniform(2.0, 3.0))
                resp2 = requests.post(ajax_url, data=data, headers=HEADERS, timeout=15)

                if resp2.status_code != 200 or len(resp2.text) < 100:
                    print(f"  加载更多第 {page} 次无数据，停止")
                    break

                soup2 = BeautifulSoup(resp2.text, "html.parser")
                more_items = parse_competition_items(soup2)

                if not more_items:
                    # 如果解析不到，尝试直接搜索链接
                    for a in soup2.find_all("a", href=True):
                        title = a.get_text(strip=True)
                        href = a["href"]
                        if title and len(title) > 8 and ("竞赛" in title or "大赛" in title or "挑战" in title or "杯" in title):
                            more_items.append({
                                "name": title,
                                "url": normalize_url(href),
                                "source": "赛欢网",
                            })

                new_count = 0
                for c in more_items:
                    if c["url"] not in seen_urls and is_cs_related(c.get("name", "")):
                        seen_urls.add(c["url"])
                        all_contests.append(c)
                        new_count += 1

                print(f"  加载更多第 {page} 次: 新增 {new_count} 条, 累计 {len(all_contests)} 条")

                if new_count == 0:
                    break

            except requests.RequestException as e:
                print(f"  [ERROR] 加载更多第 {page} 次失败: {e}")
                break

    # 爬取详情页
    if fetch_details and all_contests:
        detail_count = min(len(all_contests), 30)
        print(f"\n  开始爬取详情页 (共 {detail_count}/{len(all_contests)} 条)...")
        for i, contest in enumerate(all_contests[:detail_count]):
            detail = fetch_detail_page(contest["url"])
            contest.update(detail)
            print(f"    [{i+1}/{detail_count}] {contest['name'][:35]}...")
            time.sleep(random.uniform(2.0, 3.0))

    # 保存结果
    output_file = os.path.join(OUTPUT_DIR, "saihuan_cs_contests.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_contests, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"赛欢网爬取完成!")
    print(f"  总计: {len(all_contests)} 条竞赛")
    print(f"  保存至: {output_file}")
    print(f"{'='*60}")

    return all_contests


if __name__ == "__main__":
    crawl_saihuan(max_pages=5, fetch_details=True)
