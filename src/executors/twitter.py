import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any

from ..models import ExecutorResult, UnifiedItem, SourceType

logger = logging.getLogger(__name__)

def _create_unified_item(tweet: Dict[str, Any], collected_at: datetime) -> UnifiedItem:
    """Tweetデータを統一形式に変換"""

    content_id = f"twitter_{hashlib.md5(tweet['text'].encode()).hexdigest()[:8]}"

    # Tweetの場合、textが短いのでそのまま要約として使用
    summary = tweet['text'][:200] + "..." if len(tweet['text']) > 200 else tweet['text']

    return UnifiedItem(
        id=content_id,
        title=f"Tweet by {tweet['author']}",
        summary=summary,
        url=tweet['url'],
        source='twitter',
        source_type=SourceType.SOCIAL,
        published_at=datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00') if 'Z' in tweet['timestamp'] else tweet['timestamp']),
        collected_at=collected_at
    )

async def twitter_fetcher(config: Dict[str, Any]) -> ExecutorResult:
    """Twitter投稿取得（Level 1フォーマット対応版）"""

    accounts = config.get("accounts", ["@openai", "@huggingface"])
    keywords = config.get("keywords", ["AI", "machine learning"])
    max_tweets = config.get("max_tweets", 50)
    use_mock = config.get("use_mock", True)  # デフォルトではモックを使用

    logger.info(f"Fetching Twitter data: {len(accounts)} accounts, {len(keywords)} keywords")

    collected_at = datetime.now()

    if use_mock:
        # モックデータ（テスト用）
        await asyncio.sleep(0.5)

        # よりリアルなTwitterサンプルデータ
        sample_tweets = [
            {
                "text": "Excited to announce our new AI research breakthrough in multimodal understanding! 🚀 #AI #MachineLearning",
                "author": "@openai",
                "url": "https://twitter.com/openai/status/sample1",
                "keyword": "AI",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "likes": 2847,
                "retweets": 892
            },
            {
                "text": "New Transformers library update with improved performance and memory efficiency! Check it out 🤗",
                "author": "@huggingface",
                "url": "https://twitter.com/huggingface/status/sample2",
                "keyword": "machine learning",
                "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
                "likes": 1567,
                "retweets": 445
            },
            {
                "text": "The future of AI is multimodal. Combining vision, language, and reasoning capabilities will unlock new possibilities.",
                "author": "@openai",
                "url": "https://twitter.com/openai/status/sample3",
                "keyword": "AI",
                "timestamp": (datetime.now() - timedelta(hours=8)).isoformat(),
                "likes": 3421,
                "retweets": 1204
            },
            {
                "text": "Open source AI models are democratizing access to cutting-edge technology. What are you building with them?",
                "author": "@huggingface",
                "url": "https://twitter.com/huggingface/status/sample4",
                "keyword": "machine learning",
                "timestamp": (datetime.now() - timedelta(hours=12)).isoformat(),
                "likes": 987,
                "retweets": 234
            }
        ]

        # キーワードとアカウントに基づいてフィルタリング
        tweets = []
        for keyword in keywords:
            keyword_tweets = [t for t in sample_tweets if keyword.lower() in t['text'].lower()]
            tweets.extend(keyword_tweets[:max_tweets // len(keywords)])

        # 不足分は汎用的なツイートで補完
        remaining = min(max_tweets - len(tweets), 10)  # 最大10個まで
        for i in range(remaining):
            account = accounts[i % len(accounts)]
            keyword = keywords[i % len(keywords)]
            tweets.append({
                "text": f"Sample tweet about {keyword} from {account}. This is auto-generated content for testing purposes.",
                "author": account,
                "url": f"https://twitter.com{account}/status/gen{i}",
                "keyword": keyword,
                "timestamp": (datetime.now() - timedelta(hours=i+1)).isoformat(),
                "likes": (i + 1) * 15,
                "retweets": (i + 1) * 5
            })

    else:
        # TODO: 実際のTwitter API実装
        logger.info("Twitter API not implemented yet, using fallback data")
        tweets = [
            {
                "text": f"Fallback tweet about {keyword}",
                "author": account,
                "url": f"https://twitter.com{account}/fallback{i}",
                "keyword": keyword,
                "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                "likes": i * 20,
                "retweets": i * 6
            }
            for i, (account, keyword) in enumerate(zip(accounts, keywords), 1)
        ]

    # 統一形式に変換
    unified_items = []
    for tweet in tweets:
        try:
            unified_item = _create_unified_item(tweet, collected_at)
            unified_items.append(unified_item)
        except Exception as e:
            logger.warning(f"Failed to convert Tweet to unified format: {e}")
            continue

    return {
        "unified_items": [item.model_dump() for item in unified_items],
        "count": len(unified_items),
        "source": "twitter",
        "source_type": "social",
        "collected_at": collected_at.isoformat()
    }
