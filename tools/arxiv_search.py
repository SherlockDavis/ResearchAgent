"""arXiv搜索工具"""
import asyncio
from typing import List, Dict, Any, Optional
import arxiv
from dataclasses import dataclass
from config import get_settings
from utils.logger import logger


@dataclass
class ArxivPaper:
    """arXiv论文数据结构"""
    title: str
    authors: List[str]
    summary: str
    arxiv_id: str
    pdf_url: str
    published: str
    primary_category: str
    categories: List[str]


class ArxivSearcher:
    """arXiv论文搜索器"""

    def __init__(self):
        self.settings = get_settings()
        self.client = arxiv.Client()

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
    ) -> List[ArxivPaper]:
        """搜索arXiv论文

        Args:
            query: 搜索查询
            max_results: 最大结果数
            sort_by: 排序方式

        Returns:
            论文列表
        """
        if max_results is None:
            max_results = self.settings.ARXIV_MAX_RESULTS

        logger.info(f"Searching arXiv for: {query}")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by,
        )

        papers = []
        try:
            for result in self.client.results(search):
                paper = ArxivPaper(
                    title=result.title,
                    authors=[str(author) for author in result.authors],
                    summary=result.summary,
                    arxiv_id=result.entry_id.split("/")[-1],
                    pdf_url=result.pdf_url,
                    published=result.published.isoformat(),
                    primary_category=result.primary_category,
                    categories=result.categories,
                )
                papers.append(paper)

            logger.info(f"Found {len(papers)} papers")
            return papers

        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            raise

    async def search_async(
        self,
        query: str,
        max_results: Optional[int] = None,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
    ) -> List[ArxivPaper]:
        """异步搜索arXiv论文"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.search, query, max_results, sort_by
        )

    def search_by_ids(self, arxiv_ids: List[str]) -> List[ArxivPaper]:
        """通过arXiv ID搜索论文"""
        papers = []
        for arxiv_id in arxiv_ids:
            try:
                search = arxiv.Search(id_list=[arxiv_id])
                for result in self.client.results(search):
                    paper = ArxivPaper(
                        title=result.title,
                        authors=[str(author) for author in result.authors],
                        summary=result.summary,
                        arxiv_id=result.entry_id.split("/")[-1],
                        pdf_url=result.pdf_url,
                        published=result.published.isoformat(),
                        primary_category=result.primary_category,
                        categories=result.categories,
                    )
                    papers.append(paper)
            except Exception as e:
                logger.error(f"Error fetching paper {arxiv_id}: {e}")
                continue

        return papers


def format_papers_for_prompt(papers: List[ArxivPaper]) -> str:
    """将论文列表格式化为prompt字符串"""
    formatted = []
    for i, paper in enumerate(papers, 1):
        formatted.append(
            f"[{i}] {paper.title}\n"
            f"Authors: {', '.join(paper.authors)}\n"
            f"Abstract: {paper.summary[:500]}...\n"
            f"URL: {paper.pdf_url}\n"
        )
    return "\n---\n".join(formatted)
