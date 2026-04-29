"""
计算机竞赛爬虫 - 主入口
依次运行: 赛氪爬虫 → 赛欢网爬虫 → 数据合并
"""

import sys
import os

# 将当前目录加入 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from saikr_spider import crawl_saikr
from saihuan_spider import crawl_saihuan
from merge_data import merge_contests


def main():
    print("=" * 60)
    print("  计算机竞赛爬虫 - 开始运行")
    print("=" * 60)

    # 第1步：爬取赛氪
    print("\n[1/3] 爬取赛氪网...")
    saikr_data = crawl_saikr(max_pages_per_category=5)

    # 第2步：爬取赛欢网
    print("\n[2/3] 爬取赛欢网...")
    saihuan_data = crawl_saihuan(max_pages=3, fetch_details=True)

    # 第3步：合并去重
    print("\n[3/3] 合并数据...")
    merged = merge_contests()

    print("\n" + "=" * 60)
    print("  全部完成!")
    print(f"  总计爬取: {len(merged)} 条计算机竞赛")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    print(f"  输出目录: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
