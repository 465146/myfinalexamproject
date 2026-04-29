"""
爬虫合并与去重脚本
- 合并赛氪和赛欢网的爬取结果
- 按竞赛名称去重
- 输出统一格式的 JSON
"""

import json
import os
import re

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def normalize_name(name):
    """标准化竞赛名称，用于去重比较"""
    # 去除年份差异、空格等
    name = re.sub(r"\s+", "", name)
    name = re.sub(r"[（()【\[\]】]", "", name)
    name = name.replace("第", "").replace("届", "")
    return name.lower()


def merge_contests(saikr_file=None, saihuan_file=None):
    """合并去重竞赛数据"""
    saikr_data = []
    saihuan_data = []

    if saikr_file is None:
        saikr_file = os.path.join(OUTPUT_DIR, "saikr_cs_contests.json")
    if saihuan_file is None:
        saihuan_file = os.path.join(OUTPUT_DIR, "saihuan_cs_contests.json")

    if os.path.exists(saikr_file):
        with open(saikr_file, "r", encoding="utf-8") as f:
            saikr_data = json.load(f)
        print(f"赛氪数据: {len(saikr_data)} 条")
    else:
        print(f"赛氪数据文件不存在: {saikr_file}")

    if os.path.exists(saihuan_file):
        with open(saihuan_file, "r", encoding="utf-8") as f:
            saihuan_data = json.load(f)
        print(f"赛欢网数据: {len(saihuan_data)} 条")
    else:
        print(f"赛欢网数据文件不存在: {saihuan_file}")

    # 合并，赛氪数据优先（字段更完整）
    merged = []
    seen_names = set()

    # 先加入赛氪数据
    for c in saikr_data:
        key = normalize_name(c.get("name", ""))
        if key and key not in seen_names:
            seen_names.add(key)
            merged.append({
                "name": c.get("name", ""),
                "category": c.get("category", ""),
                "level": c.get("level", ""),
                "organizer": c.get("organizer", ""),
                "scope": c.get("scope", ""),
                "regist_start": c.get("regist_start", ""),
                "regist_end": c.get("regist_end", ""),
                "contest_start": c.get("contest_start", ""),
                "contest_end": c.get("contest_end", ""),
                "status": c.get("status", ""),
                "description": c.get("description", ""),
                "url": c.get("url", ""),
                "source": c.get("source", ""),
            })

    # 再加入赛欢网数据（去重）
    saihuan_added = 0
    for c in saihuan_data:
        key = normalize_name(c.get("name", ""))
        if key and key not in seen_names:
            seen_names.add(key)
            merged.append({
                "name": c.get("name", ""),
                "category": c.get("category", c.get("tags", "")),
                "level": c.get("level", ""),
                "organizer": c.get("organizer", ""),
                "scope": "",
                "regist_start": c.get("regist_time", ""),
                "regist_end": "",
                "contest_start": c.get("contest_time", ""),
                "contest_end": "",
                "status": "",
                "description": c.get("description", ""),
                "url": c.get("url", ""),
                "source": c.get("source", ""),
            })
            saihuan_added += 1

    print(f"\n合并结果: 赛氪 {len(saikr_data)} 条 + 赛欢网新增 {saihuan_added} 条 = 共 {len(merged)} 条 (去重后)")

    # 保存合并结果
    output_file = os.path.join(OUTPUT_DIR, "all_cs_contests.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"合并数据保存至: {output_file}")

    # 生成统计
    stats = {}
    for c in merged:
        cat = c.get("category", "未分类")
        stats[cat] = stats.get(cat, 0) + 1

    print("\n分类统计:")
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} 条")

    return merged


if __name__ == "__main__":
    merge_contests()
