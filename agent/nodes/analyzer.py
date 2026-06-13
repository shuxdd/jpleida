"""
分析对比节点
============

对提取的信息进行多维度分析对比。
"""

import json
import logging
from typing import Dict, List, Any
from collections import Counter
import re
from agent.graph_state import AgentState
from agent.llm import create_llm
from collector.cleaner import DataCleaner
from config.prompts import SWOT_PROMPT
from utils.llm_parser import extract_json_from_llm
from utils.retry import retry_async
from agent.progress import report_progress

logger = logging.getLogger(__name__)


async def analyze_competitors(state: AgentState) -> dict:
    """
    分析对比节点

    对提取的竞品信息进行多维度分析。
    """
    logger.info("开始分析对比...")

    extracted_info = state.get("extracted_info", [])
    dimensions = state.get("dimensions", ["features", "pricing", "swot"])
    raw_data = state.get("raw_data", [])
    analysis_results = {}

    try:
        # 按竞品分组
        grouped = _group_by_competitor(extracted_info)

        # 合并每个竞品的数据
        merged_data = {}
        for competitor, entries in grouped.items():
            data_list = [e.get("extracted_info", {}) for e in entries if e.get("extracted_info")]
            if data_list:
                merged_data[competitor] = DataCleaner.merge_data(data_list)
                merged_data[competitor]["competitor_name"] = competitor

        analysis_results["competitors_data"] = merged_data

        # 按维度分析
        if "features" in dimensions:
            analysis_results["feature_matrix"] = _build_feature_matrix(merged_data)
            logger.info("  功能矩阵构建完成")

        if "pricing" in dimensions:
            analysis_results["pricing_comparison"] = _build_pricing_comparison(merged_data)
            logger.info("  定价对比完成")

        if "swot" in dimensions:
            analysis_results["swot_analysis"] = await _generate_swot(merged_data)
            logger.info("  SWOT分析完成")

        if "reviews" in dimensions:
            analysis_results["review_analysis"] = _analyze_reviews(merged_data, raw_data)
            logger.info("  用户评价分析完成")

        analysis_results["summary"] = _generate_summary(merged_data, dimensions)

        logger.info("分析对比完成")
        report_progress(state.get("progress_callback"), "analyzer")
        return {
            "analysis_results": analysis_results,
            "status": "analyzing",
            "errors": state.get("errors", [])
        }

    except Exception as e:
        logger.error(f"分析对比节点失败: {e}")
        return {
            "analysis_results": analysis_results,
            "status": "analyzing",
            "errors": state.get("errors", []) + [f"分析节点错误: {str(e)}"]
        }


def _group_by_competitor(extracted_info: List[Dict]) -> Dict[str, List[Dict]]:
    """按竞品名称分组"""
    grouped = {}
    for entry in extracted_info:
        name = entry.get("competitor", "unknown")
        if name not in grouped:
            grouped[name] = []
        grouped[name].append(entry)
    return grouped


def _build_feature_matrix(merged_data: Dict[str, Any]) -> Dict:
    """构建功能矩阵"""
    all_features = set()
    competitor_features = {}

    for name, data in merged_data.items():
        features = data.get("features", [])
        all_features.update(features)
        competitor_features[name] = set(features)

    feature_list = sorted(list(all_features))[:30]  # 最多30个功能

    matrix = {
        "features": feature_list,
        "competitors": {}
    }

    for name in merged_data:
        matrix["competitors"][name] = {
            f: f in competitor_features.get(name, set())
            for f in feature_list
        }

    return matrix


def _build_pricing_comparison(merged_data: Dict[str, Any]) -> Dict:
    """构建定价对比"""
    comparison = {"competitors": {}}

    for name, data in merged_data.items():
        prices = data.get("prices", [])
        if prices:
            comparison["competitors"][name] = {
                "prices": prices,
                "min_price": min(p["price"] for p in prices if "price" in p),
                "max_price": max(p["price"] for p in prices if "price" in p),
                "currency": prices[0].get("currency", "CNY") if prices else "CNY"
            }
        else:
            comparison["competitors"][name] = {"prices": [], "note": "未找到定价信息"}

    return comparison


async def _generate_swot(merged_data: Dict[str, Any]) -> Dict:
    """生成SWOT分析"""
    swot_results = {}

    try:
        llm = create_llm(temperature=0.3)

        for name, data in merged_data.items():
            try:
                info_str = json.dumps(data, ensure_ascii=False, default=str)[:3000]
                prompt = SWOT_PROMPT.format(competitor_info=info_str)

                response = await retry_async(lambda: llm.ainvoke(prompt))
                content = response.content

                # 解析SWOT
                swot = extract_json_from_llm(content)
                if swot is None:
                    swot = {"raw_response": content}

                swot_results[name] = swot

            except Exception as e:
                logger.warning(f"  {name} SWOT分析失败: {e}")
                swot_results[name] = {"error": str(e)}

    except Exception as e:
        logger.error(f"SWOT分析整体失败: {e}")

    return swot_results


def _classify_rating(rating: int) -> str:
    """按评分分类：>=4 正面，==3 中性，<=2 负面"""
    if rating >= 4:
        return "positive"
    elif rating <= 2:
        return "negative"
    return "neutral"


def _analyze_reviews(merged_data: Dict[str, Any], raw_data: List[Dict]) -> Dict:
    """分析用户评价（来自应用商店评论）"""
    store_reviews = _collect_store_reviews(raw_data)

    if not store_reviews:
        return {
            "note": "暂无应用商店评论数据，请确认已配置 Apify API Token",
            "competitors": list(merged_data.keys())
        }

    result = {}
    for competitor, entries in store_reviews.items():
        all_reviews: List[Dict] = []
        store_info: Dict[str, Dict] = {}

        for entry in entries:
            store = entry["source"]
            data = entry.get("data", {})
            reviews = data.get("reviews", [])
            store_info[store] = {
                "rating": data.get("rating", 0),
                "count": data.get("ratings_count", len(reviews)),
            }
            for r in reviews:
                all_reviews.append({
                    "user": r.get("user", ""),
                    "text": r.get("text", ""),
                    "rating": r.get("rating", 0),
                    "date": r.get("date", ""),
                    "source": store,
                })

        # 评分统计
        ratings = [r["rating"] for r in all_reviews if r.get("rating", 0) > 0]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

        # 情感分类（评分 >= 4 正面，== 3 中性，<= 2 负面）
        sentiment: Dict[str, list] = {"positive": [], "neutral": [], "negative": []}
        for r in all_reviews:
            cat = _classify_rating(r.get("rating", 0))
            sentiment[cat].append(r)

        # 抽取正负面关键词（纯 Python，无需 LLM）
        positive_topics = _extract_review_topics(
            [r["text"] for r in sentiment["positive"] if r.get("text")]
        )
        negative_topics = _extract_review_topics(
            [r["text"] for r in sentiment["negative"] if r.get("text")]
        )
        neutral_texts = [r["text"] for r in sentiment["neutral"] if r.get("text")]

        # 生成摘要
        summary = _make_review_summary(
            competitor, avg_rating, len(all_reviews),
            positive_topics, negative_topics, neutral_texts,
        )

        result[competitor] = {
            "rating": avg_rating,
            "total_reviews": len(all_reviews),
            "sources": store_info,
            "sentiment": {
                "positive": len(sentiment["positive"]),
                "neutral": len(sentiment["neutral"]),
                "negative": len(sentiment["negative"]),
            },
            "topics": {
                "positive": positive_topics[:5],
                "negative": negative_topics[:5],
            },
            "summary": summary,
            "recent_reviews": all_reviews[:5],
        }

    return result


def _collect_store_reviews(raw_data: List[Dict]) -> Dict[str, List[Dict]]:
    """从 raw_data 中提取应用商店评论，按竞品分组"""
    store_sources = {"google_play", "app_store"}
    grouped: Dict[str, List[Dict]] = {}

    for entry in raw_data:
        if entry.get("source") not in store_sources:
            continue
        competitor = entry.get("competitor", "")
        if not competitor:
            continue
        if competitor not in grouped:
            grouped[competitor] = []
        grouped[competitor].append(entry)

    return grouped


def _extract_review_topics(texts: List[str]) -> List[str]:
    """从评论文本中抽取高频关键词（简单频率统计）"""
    if not texts:
        return []

    combined = " ".join(texts)

    # 提取中文字符序列
    chinese_parts = re.findall(r"[一-鿿]{2,}", combined)
    chinese_text = "".join(chinese_parts)

    if not chinese_text:
        return []

    # 取高频二字组合作为关键词候选
    bigrams = [chinese_text[i:i+2] for i in range(len(chinese_text) - 1)]

    # 过滤含停用字的 bigram
    stop_chars = {"的", "了", "是", "在", "有", "和", "就", "不", "也", "都", "而", "与", "或",
                  "这", "那", "对", "把", "被", "让", "给", "为", "以", "从", "到", "上", "下"}
    bigrams = [b for b in bigrams
               if b[0] not in stop_chars and b[1] not in stop_chars and b[0] != b[1]]

    return [bg for bg, _ in Counter(bigrams).most_common(10)]


def _make_review_summary(
    competitor: str,
    avg_rating: float,
    total: int,
    positive_topics: List[str],
    negative_topics: List[str],
    neutral_texts: List[str],
) -> str:
    """生成评论文本摘要"""
    parts = [f"{competitor}共{total}条用户评价，平均评分{avg_rating}分。"]

    if positive_topics:
        parts.append(f"好评集中在：{'、'.join(positive_topics)}。")
    if negative_topics:
        parts.append(f"待改进方面：{'、'.join(negative_topics)}。")
    if neutral_texts:
        parts.append("部分用户反馈了改进建议。")

    return "".join(parts)


def _generate_summary(merged_data: Dict[str, Any], dimensions: List[str]) -> str:
    """生成分析摘要"""
    competitors = list(merged_data.keys())
    return (
        f"已完成对 {len(competitors)} 个竞品的分析，"
        f"分析维度: {', '.join(dimensions)}。"
        f"竞品: {', '.join(competitors)}。"
    )
