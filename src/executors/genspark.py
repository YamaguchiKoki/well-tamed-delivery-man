import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any

from ..models import ExecutorResult, UnifiedItem, SourceType

logger = logging.getLogger(__name__)

def _create_unified_item(news: Dict[str, Any], collected_at: datetime) -> UnifiedItem:
    """GenSparkニュース結果を統一形式に変換"""

    content_id = f"genspark_{hashlib.md5(news['keyword'].encode()).hexdigest()[:8]}"

    # 要約としてニュースサマリーを使用
    summary = news['summary'][:200] + "..." if len(news['summary']) > 200 else news['summary']

    # GenSparkの場合、主要なリンクをURLとして使用
    primary_url = news['links'][0] if news['links'] else f"https://genspark.example.com/news/{content_id}"

    return UnifiedItem(
        id=content_id,
        title=f"Tech News: {news['keyword']}",
        summary=summary,
        url=primary_url,
        source='genspark',
        source_type=SourceType.NEWS,
        published_at=news.get('published_at', collected_at),
        collected_at=collected_at
    )

async def genspark_fetcher(config: Dict[str, Any]) -> ExecutorResult:
    """GenSpark調査（Level 1フォーマット対応版）"""

    api_key = config.get("api_key")
    keywords = config.get("keywords", ["AI news", "tech trends"])
    max_results = config.get("max_results", 10)
    use_mock = config.get("use_mock", True)  # デフォルトではモックを使用

    if not use_mock and (not api_key or api_key.startswith("${")):
        logger.warning("GenSpark API key not available, using mock data")
        use_mock = True

    logger.info(f"Executing GenSpark research: {keywords}")

    collected_at = datetime.now()

    if use_mock:
        # モックデータ（テスト用）
        await asyncio.sleep(1.5)

        # よりリアルなニュースサンプル
        sample_news = [
            {
                "keyword": "AI news",
                "summary": "最新のAI業界ニュースとして、OpenAIの新しいモデル発表、GoogleのAI倫理ガイドライン更新、MicrosoftのAI統合サービス拡張などが注目されています。特に、企業向けAIサービスの実用性向上と安全性確保が重要なテーマになっています。",
                "links": [
                    "https://techcrunch.com/ai-latest-developments",
                    "https://venturebeat.com/ai-industry-news",
                    "https://arxiv.org/ai-papers-weekly"
                ],
                "confidence": 0.94,
                "source_count": 25,
                "published_at": (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                "keyword": "tech trends",
                "summary": "2025年の技術トレンドとして、量子コンピューティングの実用化、5G/6G通信技術の普及、サステナブルテクノロジーの発展が挙げられています。特に、エネルギー効率とセキュリティを重視した技術開発が活発化しています。",
                "links": [
                    "https://wired.com/tech-trends-2025",
                    "https://techreview.com/emerging-technologies",
                    "https://ieee.org/future-tech-report"
                ],
                "confidence": 0.91,
                "source_count": 18,
                "published_at": (datetime.now() - timedelta(hours=4)).isoformat()
            },
            {
                "keyword": "startup funding",
                "summary": "AI関連スタートアップの資金調達が活発化しており、特に生成AI、自動運転、ヘルスケアAI分野への投資が増加しています。ベンチャーキャピタルからの資金調達総額は前年比40%増となっています。",
                "links": [
                    "https://crunchbase.com/startup-funding-report",
                    "https://pitchbook.com/ai-investments",
                    "https://techfundingnews.com/weekly-report"
                ],
                "confidence": 0.88,
                "source_count": 12,
                "published_at": (datetime.now() - timedelta(hours=8)).isoformat()
            }
        ]

        # キーワードに基づいて結果を生成
        research_results = []
        for i, keyword in enumerate(keywords[:max_results]):
            if i < len(sample_news):
                result = sample_news[i].copy()
                result['keyword'] = keyword  # 実際のキーワードで上書き
            else:
                result = {
                    "keyword": keyword,
                    "summary": f"{keyword}に関する最新ニュース分析。業界動向、技術革新、市場の変化について包括的にまとめた情報です。",
                    "links": [
                        f"https://news.example.com/{keyword.replace(' ', '-').lower()}",
                        f"https://techreport.ai/{keyword.replace(' ', '-').lower()}",
                        f"https://industry.news/{keyword.replace(' ', '-').lower()}"
                    ],
                    "confidence": 0.85,
                    "source_count": 10 + i,
                    "published_at": (datetime.now() - timedelta(hours=i+1)).isoformat()
                }
            research_results.append(result)

    else:
        # TODO: 実際のGenSpark API実装
        logger.info("GenSpark API not implemented yet, using fallback data")
        research_results = [
            {
                "keyword": keyword,
                "summary": f"Fallback news summary for '{keyword}'. This would contain actual news aggregation results.",
                "links": [
                    f"https://fallback.news/{keyword.replace(' ', '-').lower()}"
                ],
                "confidence": 0.75,
                "source_count": 8,
                "published_at": (datetime.now() - timedelta(hours=i)).isoformat()
            }
            for i, keyword in enumerate(keywords[:5])
        ]

    # 統一形式に変換
    unified_items = []
    for news in research_results:
        try:
            unified_item = _create_unified_item(news, collected_at)
            unified_items.append(unified_item)
        except Exception as e:
            logger.warning(f"Failed to convert GenSpark news to unified format: {e}")
            continue

    return {
        "unified_items": [item.model_dump() for item in unified_items],
        "count": len(unified_items),
        "source": "genspark",
        "source_type": "news",
        "collected_at": collected_at.isoformat()
    }
