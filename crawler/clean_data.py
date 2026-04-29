"""
竞赛数据清洗 & 信息提取
- 清理 description 中的噪声（广告、打赏、猜你喜欢等）
- 从 description 中提取有价值信息补充空白字段
- 重构为精炼的自然语言知识片段，适合 RAG 检索
"""

import json
import os
import re

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# 需要过滤的噪声行关键词
NOISE_PATTERNS = [
    r"打赏", r"扫码", r"支付宝", r"微信.*扫", r"QQ钱包",
    r"赞赏支持", r"打赏助手", r"你说多少就多少",
    r"猜你喜欢", r"上一篇", r"下一篇",
    r"自定义", r"2\s*5\s*10\s*20\s*50",  # 打赏金额
    r"言语也许对你并不重要", r"真想不到",
    r"打开支付宝扫一扫", r"打开微信扫一扫", r"打开QQ钱包扫一扫",
    r"大赛来源：.*$",  # 来源链接
    r"附件下载.*$",  # 附件下载区
    r"赛事咨询.*\d{11}",  # 电话号码行
    r"赛事监督.*\d{8}",  # 监督电话
    r"赛事邮箱.*@",  # 邮箱行
]

# 从 description 中提取信息的正则模式
EXTRACT_PATTERNS = {
    "participants": [
        r"参赛对象[：:]\s*(.+?)(?:\n|四|五|六|$)",
        r"参赛人员[：:]\s*(.+?)(?:\n|四|五|六|$)",
        r"面向.*?(?:在校|学生|大学生)(.+?)(?:\n|$)",
    ],
    "contest_fee": [
        r"参赛费用?[：:]\s*(.+?)(?:\n|六|七|八|$)",
        r"报名费[：:]\s*(.+?)(?:\n|$)",
        r"每队.*?元.*?(?:\n|$)",
    ],
    "team_requirement": [
        r"每(?:个)?团队\d+[-—]\d+人",
        r"每队\d+[-—]\d+人",
        r"可跨校组队",
        r"每位同学只能参加一个团队",
    ],
    "official_website": [
        r"(?:大赛|比赛|竞赛)官网[：:]\s*(https?://[^\s\n]+)",
        r"(https?://[a-zA-Z0-9.-]+\.[a-z]{2,}[/\w.-]*)",
    ],
}


def clean_description(text):
    """清理 description 中的噪声文本"""
    if not text:
        return ""
    
    lines = text.split("\n")
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检查是否匹配噪声模式
        is_noise = False
        for pattern in NOISE_PATTERNS:
            if re.search(pattern, line):
                is_noise = True
                break
        
        if not is_noise:
            cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines)


def extract_info_from_description(desc):
    """从 description 中提取结构化信息"""
    extracted = {}
    
    for field, patterns in EXTRACT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, desc, re.DOTALL)
            if match:
                if field == "official_website":
                    extracted[field] = match.group(1).strip()
                elif field == "team_requirement":
                    # 收集所有匹配的组队要求
                    all_matches = re.findall(pattern, desc)
                    if all_matches:
                        extracted[field] = "；".join(set(all_matches))
                else:
                    value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                    # 截断过长的提取结果
                    if len(value) > 300:
                        value = value[:300] + "..."
                    extracted[field] = value
                break
    
    return extracted


def extract_schedule_from_description(desc):
    """从 description 中提取赛程安排"""
    schedule_parts = []
    
    # 匹配更简单的模式：XX赛 + 时间
    simple_pattern = re.findall(
        r"(初赛|复赛|决赛|分赛区决赛|全国总决赛|校内选拔赛|作品提交)[^：:\n]*[：:]\s*"
        r"([^。\n]{4,40})",
        desc
    )
    
    if simple_pattern:
        for stage, time_info in simple_pattern:
            schedule_parts.append(f"{stage}：{time_info.strip()}")
    
    return "；".join(schedule_parts) if schedule_parts else ""


def format_time_field(start, end):
    """格式化时间字段"""
    if start and end:
        # 去掉时分秒，只保留日期
        s = start.split(" ")[0] if " " in start else start
        e = end.split(" ")[0] if " " in end else end
        return f"{s} ~ {e}"
    elif start:
        return start.split(" ")[0] if " " in start else start
    elif end:
        return end.split(" ")[0] if " " in end else end
    return ""


def build_knowledge_text(contest, extracted_info, schedule):
    """将竞赛数据重构为精炼的自然语言知识片段"""
    parts = []
    
    # 名称
    name = contest.get("name", "")
    parts.append(name)
    
    # 级别
    level = contest.get("level", "") or extracted_info.get("level", "")
    if level:
        parts.append(f"级别：{level}")
    
    # 分类
    category = contest.get("category", "")
    if category:
        parts.append(f"类别：{category}")
    
    # 主办方
    organizer = contest.get("organizer", "")
    if organizer:
        parts.append(f"主办方：{organizer}")
    
    # 参赛对象
    participants = extracted_info.get("participants", "")
    if participants:
        parts.append(f"参赛对象：{participants}")
    
    # 组队要求
    team_req = extracted_info.get("team_requirement", "")
    if team_req:
        parts.append(f"组队要求：{team_req}")
    
    # 报名时间
    regist_time = format_time_field(
        contest.get("regist_start", ""),
        contest.get("regist_end", "")
    )
    if regist_time:
        parts.append(f"报名时间：{regist_time}")
    
    # 赛程安排
    if schedule:
        parts.append(f"赛程安排：{schedule}")
    
    # 比赛时间
    contest_time = format_time_field(
        contest.get("contest_start", ""),
        contest.get("contest_end", "")
    )
    if contest_time:
        parts.append(f"比赛时间：{contest_time}")
    
    # 参赛费用
    fee = extracted_info.get("contest_fee", "")
    if fee:
        parts.append(f"参赛费用：{fee}")
    
    # 官网
    website = extracted_info.get("official_website", "") or contest.get("url", "")
    if website:
        parts.append(f"官网：{website}")
    
    return "\n".join(parts)


def process_contest(contest):
    """处理单条竞赛数据"""
    # 清理 description
    raw_desc = contest.get("description", "")
    cleaned_desc = clean_description(raw_desc)
    
    # 从 description 提取信息
    extracted_info = extract_info_from_description(raw_desc)
    
    # 提取赛程安排
    schedule = extract_schedule_from_description(raw_desc)
    
    # 构建知识文本
    knowledge_text = build_knowledge_text(contest, extracted_info, schedule)
    
    # 构建清洗后的结构化数据
    result = {
        "name": contest.get("name", ""),
        "category": contest.get("category", ""),
        "level": contest.get("level", "") or extracted_info.get("level", ""),
        "organizer": contest.get("organizer", ""),
        "scope": contest.get("scope", ""),
        "regist_time": format_time_field(
            contest.get("regist_start", ""),
            contest.get("regist_end", "")
        ),
        "contest_time": format_time_field(
            contest.get("contest_start", ""),
            contest.get("contest_end", "")
        ),
        "schedule": schedule,
        "participants": extracted_info.get("participants", ""),
        "team_requirement": extracted_info.get("team_requirement", ""),
        "contest_fee": extracted_info.get("contest_fee", ""),
        "official_website": extracted_info.get("official_website", "") or contest.get("url", ""),
        "status": contest.get("status", ""),
        "url": contest.get("url", ""),
        "source": contest.get("source", ""),
        "knowledge_text": knowledge_text,  # RAG 用的知识片段
    }
    
    return result


def clean_all_data(input_file=None, output_file=None, preview_only=5):
    """
    清洗所有竞赛数据
    preview_only: 只预览前N条，0表示处理全部
    """
    if input_file is None:
        input_file = os.path.join(OUTPUT_DIR, "all_cs_contests.json")
    if output_file is None:
        output_file = os.path.join(OUTPUT_DIR, "all_cs_contests_cleaned.json")
    
    with open(input_file, "r", encoding="utf-8") as f:
        contests = json.load(f)
    
    # 过滤掉赛欢网数据（description脏，正则提取效果差）
    saihuan_count = sum(1 for c in contests if c.get("source") == "赛欢网")
    contests = [c for c in contests if c.get("source") != "赛欢网"]
    
    print(f"加载原始数据: {len(contests) + saihuan_count} 条")
    print(f"过滤赛欢网: {saihuan_count} 条 (丢弃)")
    print(f"剩余赛氪数据: {len(contests)} 条")
    print(f"{'='*60}")
    
    # 处理数据
    limit = preview_only if preview_only > 0 else len(contests)
    results = []
    
    for i, contest in enumerate(contests[:limit]):
        result = process_contest(contest)
        results.append(result)
        
        # 打印预览
        if preview_only > 0:
            print(f"\n--- 第 {i+1} 条 ---")
            print(f"原始数据字段数: {len(contest)}")
            print(f"原始 description 长度: {len(contest.get('description', ''))}")
            print(f"\n📝 知识片段预览:")
            print(result["knowledge_text"])
            print(f"\n{'─'*40}")
    
    # 统计
    has_knowledge = sum(1 for r in results if len(r["knowledge_text"]) > 50)
    has_schedule = sum(1 for r in results if r["schedule"])
    has_participants = sum(1 for r in results if r["participants"])
    has_fee = sum(1 for r in results if r["contest_fee"])
    
    print(f"\n{'='*60}")
    print(f"处理结果统计 (预览 {limit} 条):")
    print(f"  有实质知识内容: {has_knowledge}/{limit}")
    print(f"  提取到赛程安排: {has_schedule}/{limit}")
    print(f"  提取到参赛对象: {has_participants}/{limit}")
    print(f"  提取到参赛费用: {has_fee}/{limit}")
    
    # 保存（即使预览也保存，方便查看）
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n保存至: {output_file}")
    
    return results


if __name__ == "__main__":
    import sys
    # 默认预览5条，传 --all 处理全部
    if "--all" in sys.argv:
        clean_all_data(preview_only=0)
    else:
        print("🔍 试水模式：预览前 5 条清洗结果\n")
        clean_all_data(preview_only=5)
        print("\n💡 确认没问题后，运行: python crawler/clean_data.py --all")
