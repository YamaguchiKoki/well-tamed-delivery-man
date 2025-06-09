import asyncio
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any

from ..models import ExecutorResult, UnifiedItem, SourceType

logger = logging.getLogger(__name__)

def _create_unified_item(research: Dict[str, Any], collected_at: datetime) -> UnifiedItem:
    """ChatGPT調査結果を統一形式に変換"""

    content_id = f"chatgpt_{hashlib.md5(research['query'].encode()).hexdigest()[:8]}"

    # 要約として研究結果のサマリーを使用
    summary = research['summary'][:200] + "..." if len(research['summary']) > 200 else research['summary']

    # ChatGPTの場合、URLは調査元ではなく仮想的なレポートURL
    report_url = f"https://chatgpt-research.example.com/report/{content_id}"

    return UnifiedItem(
        id=content_id,
        title=f"AI Research: {research['query']}",
        summary=summary,
        url=report_url,
        source='chatgpt',
        source_type=SourceType.LLM,
        published_at=collected_at,  # LLM生成なので現在時刻
        collected_at=collected_at
    )

async def chatgpt_fetcher(config: Dict[str, Any]) -> ExecutorResult:
    """ChatGPT調査（Level 1フォーマット対応版）"""

    api_key = config.get("api_key")
    queries = config.get("queries", ["AI技術動向 2025", "機械学習最新研究"])
    model = config.get("model", "gpt-4o")
    max_tokens = config.get("max_tokens", 2000)
    use_mock = config.get("use_mock", True)  # デフォルトではモックを使用

    if not use_mock and (not api_key or api_key.startswith("${")):
        logger.warning("OpenAI API key not available, using mock data")
        use_mock = True

    logger.info(f"Executing ChatGPT research: {len(queries)} queries")

    collected_at = datetime.now()

    if use_mock:
        # モックデータ（テスト用）
        await asyncio.sleep(2)

        # よりリアルなChatGPT調査結果サンプル
        sample_research = [
            {
                "query": "AI技術動向 2025",
                "summary": "2025年のAI技術動向として、マルチモーダルAIの普及、エッジAIの高性能化、AI倫理とガバナンスの制度化が主要なトレンドとして挙げられます。特に、視覚・言語・音声を統合したAIシステムが実用化段階に入り、様々な産業で活用が進んでいます。",
                "key_points": [
                    "マルチモーダルAIシステムの実用化加速",
                    "エッジAIチップの性能向上とコスト削減",
                    "AI規制フレームワークの国際標準化",
                    "生成AIの企業導入率50%超達成",
                    "AIエネルギー効率の大幅改善"
                ],
                "sources": [
                    "https://arxiv.org/ai-trends-2025",
                    "https://techreport.ai/2025-outlook"
                ],
                "confidence": 0.92,
                "model_used": model,
                "tokens_used": 1456
            },
            {
                "query": "機械学習最新研究",
                "summary": "機械学習分野では、Transformer架構の効率化、自己教師あり学習の進歩、フェデレーテッドラーニングの実用化が注目されています。特に、計算効率を大幅に改善した新しいアテンション機構や、少量データでの高精度学習を可能にする手法が次々と発表されています。",
                "key_points": [
                    "効率的なTransformerアーキテクチャの開発",
                    "自己教師あり学習による汎化性能向上",
                    "フェデレーテッドラーニングの産業応用",
                    "NeRFと3D AI技術の融合",
                    "量子機械学習アルゴリズムの実用化"
                ],
                "sources": [
                    "https://neurips.cc/latest-research",
                    "https://mlresearch.org/2025-breakthroughs"
                ],
                "confidence": 0.89,
                "model_used": model,
                "tokens_used": 1678
            }
        ]

        # クエリに応じた結果を生成
        research_results = []
        for i, query in enumerate(queries[:3]):
            if i < len(sample_research):
                result = sample_research[i].copy()
                result['query'] = query  # 実際のクエリで上書き
            else:
                result = {
                    "query": query,
                    "summary": f"最新の{query}に関する包括的な調査結果。技術的進歩、市場動向、将来展望を含む詳細な分析結果です。",
                    "key_points": [
                        f"{query}における技術革新",
                        f"{query}の市場への影響",
                        f"{query}の将来的な可能性"
                    ],
                    "sources": [
                        f"https://research.example.com/{query.replace(' ', '-').lower()}",
                        f"https://analysis.ai/{query.replace(' ', '-').lower()}"
                    ],
                    "confidence": 0.85,
                    "model_used": model,
                    "tokens_used": max_tokens // 2
                }
            research_results.append(result)

    else:
        # TODO: 実際のOpenAI API実装
        logger.info("OpenAI API not implemented yet, using fallback data")
        research_results = [
            {
                "query": query,
                "summary": f"Fallback research summary for '{query}'. This would contain actual AI-generated insights.",
                "key_points": [
                    f"Fallback insight 1 for {query}",
                    f"Fallback insight 2 for {query}"
                ],
                "sources": [
                    f"https://fallback.ai/research/{i}"
                ],
                "confidence": 0.75,
                "model_used": model,
                "tokens_used": max_tokens // 3
            }
            for i, query in enumerate(queries[:2])
        ]

    # 統一形式に変換
    unified_items = []
    for research in research_results:
        try:
            unified_item = _create_unified_item(research, collected_at)
            unified_items.append(unified_item)
        except Exception as e:
            logger.warning(f"Failed to convert ChatGPT research to unified format: {e}")
            continue

    return {
        "unified_items": [item.model_dump() for item in unified_items],
        "count": len(unified_items),
        "source": "chatgpt",
        "source_type": "llm",
        "collected_at": collected_at.isoformat()
    }
