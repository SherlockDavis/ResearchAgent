"""Searcher Agent - 论文检索与搜索"""
import json
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base import BaseAgent
from utils.llm import create_llm
from utils.state import add_message, PaperInfo
from utils.logger import logger
from tools.arxiv_search import ArxivSearcher, format_papers_for_prompt


class SearcherAgent(BaseAgent):
    """Searcher Agent负责检索相关学术论文

    职责：
    1. 根据任务描述生成优化的搜索查询
    2. 调用arXiv API检索论文
    3. 对检索结果进行初步筛选和排序
    4. 将论文信息整理为结构化数据
    """

    def __init__(self, llm=None):
        super().__init__(name="Searcher", llm=llm)
        if self.llm is None:
            self.llm = create_llm()
        self.searcher = ArxivSearcher()
        self._load_prompt()

    def _load_prompt(self) -> None:
        """加载Searcher的系统Prompt"""
        try:
            with open("prompts/searcher.txt", "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            self.system_prompt = self._get_default_prompt()
            logger.warning("searcher.txt not found, using default prompt")

    def _get_default_prompt(self) -> str:
        """获取默认的系统Prompt"""
        return """你是一个专业的学术论文搜索专家。你的职责是帮助用户找到最相关的学术论文。

## 核心职责
1. 理解用户的搜索需求和研究问题
2. 生成优化的arXiv搜索查询
3. 对检索结果进行相关性评估

## 搜索策略
1. 提取关键词：从任务描述中提取核心概念、方法、技术
2. 构建查询：使用arXiv支持的搜索语法（如ti:标题, au:作者, abs:摘要）
3. 组合查询：可以使用AND/OR组合多个关键词

## arXiv搜索语法
- ti:关键词 - 搜索标题
- abs:关键词 - 搜索摘要
- au:作者名 - 搜索作者
- cat:分类 - 搜索分类（如cs.CL, cs.LG, cs.AI）
- AND/OR - 逻辑组合

## 输出格式
你必须以JSON格式输出，格式如下：
{
    "search_queries": [
        "ti:关键词1 AND abs:关键词2",
        "cat:cs.CL AND abs:关键词"
    ],
    "max_results": 10,
    "sort_by": "relevance",
    "search_strategy": "搜索策略说明"
}

请确保输出是有效的JSON格式。"""

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行Searcher任务

        Args:
            state: 当前状态，包含query和sub_tasks

        Returns:
            更新后的状态，包含papers
        """
        # 获取当前任务描述
        task_desc = self._get_current_task_description(state)
        if not task_desc:
            task_desc = state.get("query", "")

        logger.info(f"Searcher开始检索论文: {task_desc[:100]}...")
        add_message(state, "Searcher", f"开始检索论文: {task_desc}")

        try:
            # 使用LLM生成搜索策略
            search_config = await self._generate_search_config(task_desc)

            # 执行搜索
            all_papers = []
            for query in search_config.get("search_queries", [task_desc]):
                papers = await self.searcher.search_async(
                    query=query,
                    max_results=search_config.get("max_results", 10),
                )
                all_papers.extend(papers)

            # 去重（按arxiv_id）
            seen_ids = set()
            unique_papers = []
            for paper in all_papers:
                if paper.arxiv_id not in seen_ids:
                    seen_ids.add(paper.arxiv_id)
                    unique_papers.append(paper)

            # 转换为PaperInfo并更新状态
            paper_infos = []
            for paper in unique_papers:
                paper_info = PaperInfo(
                    title=paper.title,
                    authors=paper.authors,
                    abstract=paper.summary,
                    url=f"https://arxiv.org/abs/{paper.arxiv_id}",
                    pdf_url=paper.pdf_url,
                    published=paper.published,
                    arxiv_id=paper.arxiv_id,
                )
                paper_infos.append(paper_info.to_dict())

            state["papers"] = paper_infos
            state["current_step"] = "search_completed"

            # 添加日志
            add_message(
                state,
                "Searcher",
                f"检索完成，找到{len(paper_infos)}篇相关论文"
            )

            # 记录到记忆
            self.add_to_memory("system", self.system_prompt)
            self.add_to_memory("user", task_desc)
            self.add_to_memory(
                "assistant",
                f"找到{len(paper_infos)}篇论文"
            )

            logger.info(f"Searcher完成检索，共找到{len(paper_infos)}篇论文")

            return state

        except Exception as e:
            error_msg = f"Searcher执行失败: {str(e)}"
            logger.error(error_msg)
            add_message(state, "Searcher", error_msg)
            state["current_step"] = "search_failed"
            raise

    def _get_current_task_description(self, state: Dict[str, Any]) -> str:
        """从状态中获取当前任务描述

        Args:
            state: 当前状态

        Returns:
            任务描述
        """
        # 查找当前活动的searcher任务
        for task in state.get("sub_tasks", []):
            if task.get("agent_type") == "searcher" and task.get("status") == "pending":
                return task.get("description", "")
        return ""

    async def _generate_search_config(self, task_desc: str) -> Dict[str, Any]:
        """使用LLM生成搜索配置

        Args:
            task_desc: 任务描述

        Returns:
            搜索配置字典
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请为以下搜索任务生成搜索配置：\n\n{task_desc}")
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content

            # 解析JSON响应
            config = self._parse_search_config(content)
            return config

        except Exception as e:
            logger.warning(f"LLM生成搜索配置失败，使用默认配置: {e}")
            return {
                "search_queries": [task_desc],
                "max_results": 10,
                "sort_by": "relevance",
                "search_strategy": "使用原始任务描述作为搜索查询"
            }

    def _parse_search_config(self, content: str) -> Dict[str, Any]:
        """解析搜索配置JSON

        Args:
            content: LLM响应内容

        Returns:
            搜索配置字典
        """
        # 尝试直接解析JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试从markdown代码块中提取JSON
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

        # 尝试从文本中提取JSON
        try:
            start_idx = content.find("{")
            end_idx = content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                return json.loads(content[start_idx:end_idx+1])
        except json.JSONDecodeError:
            pass

        raise ValueError(f"无法解析搜索配置: {content[:200]}...")

    async def search_papers(
        self,
        query: str,
        max_results: int = 10,
        use_llm_optimization: bool = True
    ) -> List[Dict[str, Any]]:
        """独立搜索论文（不依赖state）

        Args:
            query: 搜索查询
            max_results: 最大结果数
            use_llm_optimization: 是否使用LLM优化搜索

        Returns:
            论文信息列表
        """
        if use_llm_optimization:
            search_config = await self._generate_search_config(query)
            queries = search_config.get("search_queries", [query])
            max_results = search_config.get("max_results", max_results)
        else:
            queries = [query]

        all_papers = []
        for q in queries:
            papers = await self.searcher.search_async(query=q, max_results=max_results)
            all_papers.extend(papers)

        # 去重
        seen_ids = set()
        unique_papers = []
        for paper in all_papers:
            if paper.arxiv_id not in seen_ids:
                seen_ids.add(paper.arxiv_id)
                paper_info = PaperInfo(
                    title=paper.title,
                    authors=paper.authors,
                    abstract=paper.summary,
                    url=f"https://arxiv.org/abs/{paper.arxiv_id}",
                    pdf_url=paper.pdf_url,
                    published=paper.published,
                    arxiv_id=paper.arxiv_id,
                )
                unique_papers.append(paper_info.to_dict())

        return unique_papers

    def format_papers_summary(self, papers: List[Dict[str, Any]]) -> str:
        """格式化论文列表为摘要文本

        Args:
            papers: 论文信息列表

        Returns:
            格式化后的文本
        """
        if not papers:
            return "未找到相关论文。"

        lines = [f"共找到 {len(papers)} 篇相关论文：\n"]
        for i, paper in enumerate(papers, 1):
            lines.append(f"{i}. {paper['title']}")
            lines.append(f"   作者: {', '.join(paper['authors'][:3])}")
            if len(paper['authors']) > 3:
                lines.append(f"      等 {len(paper['authors'])} 位作者")
            lines.append(f"   arXiv: {paper['arxiv_id']}")
            lines.append(f"   链接: {paper['url']}")
            lines.append("")

        return "\n".join(lines)
