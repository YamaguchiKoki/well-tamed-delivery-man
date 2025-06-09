import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any

from ..models import ExecutorResult, UnifiedItem, SourceType

logger = logging.getLogger(__name__)

def _create_unified_item(post: Dict[str, Any], collected_at: datetime) -> UnifiedItem:
    """Reddit投稿データを統一形式に変換"""

    content_id = f"reddit_{post['subreddit']}_{hashlib.md5(post['title'].encode()).hexdigest()[:8]}"

    # 要約を適切な長さに調整（Reddit投稿の場合、タイトルが要約になることが多い）
    summary = post.get('selftext', post['title'])[:200] + "..." if len(post.get('selftext', post['title'])) > 200 else post.get('selftext', post['title'])

    return UnifiedItem(
        id=content_id,
        title=post['title'],
        summary=summary,
        url=post['url'],
        source='reddit',
        source_type=SourceType.SOCIAL,
        published_at=datetime.fromisoformat(post['created'].replace('Z', '+00:00') if 'Z' in post['created'] else post['created']),
        collected_at=collected_at
    )

async def reddit_fetcher(config: Dict[str, Any]) -> ExecutorResult:
    """Reddit投稿取得（Level 1フォーマット対応版）"""

    subreddits = config.get("subreddits", ["MachineLearning"])
    post_limit = config.get("post_limit", 20)
    time_filter = config.get("time_filter", "day")
    use_mock = config.get("use_mock", True)  # デフォルトではモックを使用

    logger.info(f"Fetching Reddit posts: {subreddits}, limit={post_limit}")

    collected_at = datetime.now()

    if use_mock:
        # モックデータ（テスト用）
        await asyncio.sleep(1)

        # よりリアルなサンプルデータ
        sample_posts = [
            {
                "title": "What's the best machine learning framework for beginners in 2025?",
                "selftext": "I'm new to ML and wondering which framework to start with. PyTorch vs TensorFlow vs JAX?",
                "url": "https://reddit.com/r/MachineLearning/comments/sample1",
                "subreddit": "MachineLearning",
                "score": 245,
                "comments": 87,
                "created": (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                "title": "New breakthrough in transformer architecture efficiency",
                "selftext": "Researchers have developed a new attention mechanism that reduces computational complexity by 40%.",
                "url": "https://reddit.com/r/MachineLearning/comments/sample2",
                "subreddit": "MachineLearning",
                "score": 892,
                "comments": 156,
                "created": (datetime.now() - timedelta(hours=6)).isoformat()
            },
            {
                "title": "Discussion: AI Safety in production environments",
                "selftext": "How do you ensure AI systems behave safely when deployed at scale?",
                "url": "https://reddit.com/r/artificial/comments/sample3",
                "subreddit": "artificial",
                "score": 178,
                "comments": 234,
                "created": (datetime.now() - timedelta(hours=12)).isoformat()
            },
            {
                "title": "Open source LLM comparison: Llama vs Mixtral vs others",
                "selftext": "Detailed comparison of open source language models released in 2024-2025.",
                "url": "https://reddit.com/r/artificial/comments/sample4",
                "subreddit": "artificial",
                "score": 567,
                "comments": 91,
                "created": (datetime.now() - timedelta(hours=18)).isoformat()
            }
        ]

        # サブレディットに基づいてフィルタリング
        posts = []
        for subreddit in subreddits:
            subreddit_posts = [p for p in sample_posts if p['subreddit'] == subreddit]
            posts.extend(subreddit_posts[:post_limit // len(subreddits)])

        # 不足分は汎用的なポストで補完
        remaining = post_limit - len(posts)
        for i in range(remaining):
            subreddit = subreddits[i % len(subreddits)]
            posts.append({
                "title": f"Interesting discussion about AI topic #{i+1}",
                "selftext": f"This is a generated post about current trends in {subreddit}.",
                "url": f"https://reddit.com/r/{subreddit}/comments/gen{i}",
                "subreddit": subreddit,
                "score": (i + 1) * 25,
                "comments": (i + 1) * 8,
                "created": (datetime.now() - timedelta(hours=i+1)).isoformat()
            })

    else:
        # TODO: 実際のReddit API実装
        logger.info("Reddit API not implemented yet, using fallback data")
        posts = [
            {
                "title": f"Fallback post from r/{subreddit} #{i}",
                "selftext": f"This is fallback content for {subreddit}.",
                "url": f"https://reddit.com/r/{subreddit}/fallback{i}",
                "subreddit": subreddit,
                "score": i * 30,
                "comments": i * 10,
                "created": (datetime.now() - timedelta(hours=i)).isoformat()
            }
            for i, subreddit in enumerate(subreddits, 1)
            for _ in range(min(post_limit // len(subreddits), 3))
        ]

    # 統一形式に変換
    unified_items = []
    for post in posts:
        try:
            unified_item = _create_unified_item(post, collected_at)
            unified_items.append(unified_item)
        except Exception as e:
            logger.warning(f"Failed to convert Reddit post to unified format: {e}")
            continue

    return {
        "unified_items": [item.model_dump() for item in unified_items],
        "count": len(unified_items),
        "source": "reddit",
        "source_type": "social",
        "collected_at": collected_at.isoformat()
    }
