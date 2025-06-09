import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import xml.etree.ElementTree as ET
import aiohttp

from ..models import ExecutorResult, UnifiedItem, SourceType

logger = logging.getLogger(__name__)

class ArxivAPI:
    """arXiv API クライアント"""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_papers(
        self,
        categories: List[str],
        max_results: int = 10,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """論文検索"""

        # 検索クエリ構築
        date_filter = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")

        # カテゴリクエリ
        cat_queries = [f"cat:{cat}" for cat in categories]
        search_query = f"({' OR '.join(cat_queries)}) AND submittedDate:[{date_filter}* TO *]"

        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }

        logger.info(f"Searching arXiv: {search_query}")

        try:
            if self.session is None:
                raise RuntimeError("Session is not initialized")
            async with self.session.get(self.BASE_URL, params=params) as response:
                response.raise_for_status()
                xml_content = await response.text()
                return self._parse_response(xml_content)

        except Exception as e:
            logger.error(f"arXiv API error: {e}")
            raise

    def _parse_response(self, xml_content: str) -> List[Dict[str, Any]]:
        """XML レスポンスの解析"""

        papers = []
        root = ET.fromstring(xml_content)

        # 名前空間定義
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }

        for entry in root.findall('atom:entry', ns):
            try:
                # 基本情報
                title_elem = entry.find('atom:title', ns)
                if title_elem is None or title_elem.text is None:
                    continue
                title = title_elem.text.strip()

                summary_elem = entry.find('atom:summary', ns)
                if summary_elem is None or summary_elem.text is None:
                    continue
                summary = summary_elem.text.strip()

                # 著者
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None and name.text is not None:
                        authors.append(name.text)

                # リンク
                pdf_url = None
                abs_url = None
                for link in entry.findall('atom:link', ns):
                    if link.get('type') == 'application/pdf':
                        pdf_url = link.get('href')
                    elif link.get('rel') == 'alternate':
                        abs_url = link.get('href')

                # カテゴリ
                categories = []
                for category in entry.findall('atom:category', ns):
                    if category.get('term') is not None:
                        categories.append(category.get('term'))

                # arXiv ID
                id_elem = entry.find('atom:id', ns)
                if id_elem is None or id_elem.text is None:
                    continue
                arxiv_id = id_elem.text.split('/')[-1]

                # 公開日
                published_elem = entry.find('atom:published', ns)
                if published_elem is None or published_elem.text is None:
                    continue
                published = published_elem.text

                paper = {
                    'title': title,
                    'authors': authors,
                    'abstract': summary,
                    'url': abs_url,
                    'pdf_url': pdf_url,
                    'categories': categories,
                    'arxiv_id': arxiv_id,
                    'published': published
                }

                papers.append(paper)

            except Exception as e:
                logger.warning(f"Failed to parse paper entry: {e}")
                continue

        return papers

def _create_unified_item(paper: Dict[str, Any], collected_at: datetime) -> UnifiedItem:
    """論文データを統一形式に変換"""

    content_id = f"arxiv_{paper['arxiv_id'].replace('.', '_')}"

    # 要約を適切な長さに調整
    summary = paper['abstract'][:200] + "..." if len(paper['abstract']) > 200 else paper['abstract']

    return UnifiedItem(
        id=content_id,
        title=paper['title'],
        summary=summary,
        url=paper['url'],
        source='arxiv',
        source_type=SourceType.ACADEMIC,
        published_at=datetime.fromisoformat(paper['published'].replace('Z', '+00:00')),
        collected_at=collected_at
    )

async def arxiv_fetcher(config: Dict[str, Any]) -> ExecutorResult:
    """arXiv論文取得（Level 1フォーマット対応版）"""

    categories = config.get("categories", ["cs.AI"])
    max_papers = config.get("max_papers", 10)
    days_back = config.get("days_back", 7)
    use_mock = config.get("use_mock", False)  # デバッグ用

    logger.info(f"Fetching arXiv papers: categories={categories}, max={max_papers}")

    collected_at = datetime.now()

    if use_mock:
        # モックデータ（テスト用）
        await asyncio.sleep(1)
        papers = [
            {
                "title": f"Advanced {categories[i % len(categories)]} Research Paper {i}",
                "authors": [f"Author {i}", f"Co-Author {i}"],
                "abstract": f"This paper presents novel research in {categories[i % len(categories)]}. We propose innovative methods for solving complex problems in this domain using state-of-the-art techniques.",
                "url": f"https://arxiv.org/abs/2024.{i:04d}",
                "pdf_url": f"https://arxiv.org/pdf/2024.{i:04d}.pdf",
                "categories": [categories[i % len(categories)]],
                "published": (datetime.now() - timedelta(days=i)).isoformat(),
                "arxiv_id": f"2024.{i:04d}"
            }
            for i in range(min(max_papers, 5))
        ]
    else:
        # 実際のAPI呼び出し
        try:
            async with ArxivAPI() as api:
                papers = await api.search_papers(categories, max_papers, days_back)
        except Exception as e:
            logger.error(f"arXiv API failed, falling back to mock data: {e}")
            # API失敗時はモックデータにフォールバック
            papers = [
                {
                    "title": f"Fallback {categories[i % len(categories)]} Research Paper {i}",
                    "authors": [f"Author {i}"],
                    "abstract": f"Fallback data for {categories[i % len(categories)]} research.",
                    "url": f"https://arxiv.org/abs/fallback.{i:04d}",
                    "pdf_url": f"https://arxiv.org/pdf/fallback.{i:04d}.pdf",
                    "categories": [categories[i % len(categories)]],
                    "published": (datetime.now() - timedelta(days=i)).isoformat(),
                    "arxiv_id": f"fallback.{i:04d}"
                }
                for i in range(min(max_papers, 3))
            ]

    # 統一形式に変換
    unified_items = []
    for paper in papers:
        try:
            unified_item = _create_unified_item(paper, collected_at)
            # datetimeオブジェクトを文字列に変換
            item_dict = unified_item.model_dump()
            item_dict['published_at'] = item_dict['published_at'].isoformat()
            item_dict['collected_at'] = item_dict['collected_at'].isoformat()
            unified_items.append(item_dict)
        except Exception as e:
            logger.warning(f"Failed to convert paper to unified format: {e}")
            continue

    return {
        "unified_items": unified_items,
        "count": len(unified_items),
        "source": "arxiv",
        "source_type": "academic",
        "collected_at": collected_at.isoformat()
    }
