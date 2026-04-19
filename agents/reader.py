"""Reader Agent - 论文精读与核心提取"""
import json
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base import BaseAgent
from utils.llm import create_llm
from utils.state import add_message, PaperInfo
from utils.logger import logger


class ReaderAgent(BaseAgent):
    """Reader Agent负责精读论文并提取核心信息

    职责：
    1. 阅读论文标题、摘要和元数据
    2. 提取核心贡献、创新点
    3. 总结研究方法和技术路线
    4. 提取实验结果和关键结论
    5. 生成结构化的论文摘要
    """

    def __init__(self, llm=None):
        super().__init__(name="Reader", llm=llm)
        if self.llm is None:
            self.llm = create_llm()
        self._load_prompt()

    def _load_prompt(self) -> None:
        """加载Reader的系统Prompt"""
        try:
            with open("prompts/reader.txt", "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            self.system_prompt = self._get_default_prompt()
            logger.warning("reader.txt not found, using default prompt")

    def _get_default_prompt(self) -> str:
        """获取默认的系统Prompt"""
        return """你是一个专业的学术论文分析专家。你的职责是精读学术论文并提取核心信息。

## 核心职责
1. 深入理解论文的研究目标和核心贡献
2. 提取论文的创新点和技术方法
3. 总结实验设计和关键结果
4. 评估论文的局限性和未来工作

## 分析维度

1. **核心贡献 (Key Contributions)**
   - 论文解决了什么问题？
   - 主要创新点是什么？
   - 与现有工作相比有何改进？

2. **研究方法 (Methods)**
   - 采用了什么技术路线？
   - 核心算法或模型是什么？
   - 方法的优势和适用场景？

3. **实验结果 (Experiments)**
   - 在什么数据集上测试？
   - 主要评价指标和结果？
   - 与基线方法的对比？

4. **局限性 (Limitations)**
   - 方法的局限性是什么？
   - 实验的不足之处？
   - 未来改进方向？

## 输出格式
你必须以JSON格式输出，格式如下：
{
    "summary": "论文整体概述（200字以内）",
    "key_contributions": ["贡献1", "贡献2", "贡献3"],
    "methods": ["方法1", "方法2"],
    "experiments": ["实验1描述", "实验2描述"],
    "limitations": ["局限性1", "局限性2"],
    "relevance_score": 8,
    "relevance_reason": "与主题的相关性说明"
}

请确保输出是有效的JSON格式。"""

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行Reader任务

        Args:
            state: 当前状态，包含papers

        Returns:
            更新后的状态，包含paper_summaries
        """
        papers = state.get("papers", [])
        if not papers:
            logger.warning("Reader: 没有论文需要阅读")
            add_message(state, "Reader", "没有论文需要阅读")
            state["paper_summaries"] = []
            state["current_step"] = "reading_completed"
            return state

        # 获取最大阅读论文数量限制
        max_papers = state.get("max_papers", 10)

        # 如果论文数量超过限制，按相关度排序并截取
        if len(papers) > max_papers:
            logger.info(f"论文数量({len(papers)})超过限制({max_papers})，将筛选前{max_papers}篇")
            add_message(state, "Reader", f"检索到{len(papers)}篇论文，根据限制将阅读前{max_papers}篇")
            # 如果papers中有relevance_score字段则按它排序，否则保持原顺序
            try:
                papers = sorted(
                    papers,
                    key=lambda x: x.get('relevance_score', 0),
                    reverse=True
                )[:max_papers]
            except Exception:
                papers = papers[:max_papers]
        else:
            add_message(state, "Reader", f"开始阅读{len(papers)}篇论文")

        logger.info(f"Reader开始阅读{len(papers)}篇论文...")

        try:
            summaries = []
            for i, paper in enumerate(papers, 1):
                logger.info(f"Reader正在阅读第{i}/{len(papers)}篇论文: {paper.get('title', '')[:50]}...")
                add_message(state, "Reader", f"正在阅读第{i}篇论文: {paper.get('title', '')[:60]}...")

                # 阅读单篇论文
                summary = await self._read_paper(paper)
                summaries.append(summary)

            # 更新状态
            state["paper_summaries"] = summaries
            state["current_step"] = "reading_completed"

            # 添加日志
            add_message(state, "Reader", f"完成{len(summaries)}篇论文的阅读和分析")

            # 记录到记忆
            self.add_to_memory("system", self.system_prompt)
            self.add_to_memory("user", f"阅读了{len(papers)}篇论文")
            self.add_to_memory("assistant", f"生成了{len(summaries)}篇摘要")

            logger.info(f"Reader完成阅读，共生成{len(summaries)}篇摘要")

            return state

        except Exception as e:
            error_msg = f"Reader执行失败: {str(e)}"
            logger.error(error_msg)
            add_message(state, "Reader", error_msg)
            state["current_step"] = "reading_failed"
            raise

    async def _read_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """阅读单篇论文并生成摘要

        Args:
            paper: 论文信息字典

        Returns:
            论文摘要字典
        """
        # 构建论文文本
        paper_text = self._format_paper_for_reading(paper)

        # 构建消息
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请阅读以下论文并提取核心信息：\n\n{paper_text}")
        ]

        try:
            # 调用LLM生成摘要
            response = await self.llm.ainvoke(messages)
            content = response.content

            # 解析JSON响应
            summary_data = self._parse_summary_response(content)

            # 合并原始论文信息和摘要
            result = {
                "arxiv_id": paper.get("arxiv_id"),
                "title": paper.get("title"),
                "authors": paper.get("authors", []),
                "url": paper.get("url"),
                "pdf_url": paper.get("pdf_url"),
                "published": paper.get("published"),
                **summary_data
            }

            return result

        except Exception as e:
            logger.error(f"阅读论文失败 {paper.get('arxiv_id')}: {e}")
            # 返回基础信息
            return {
                "arxiv_id": paper.get("arxiv_id"),
                "title": paper.get("title"),
                "authors": paper.get("authors", []),
                "url": paper.get("url"),
                "pdf_url": paper.get("pdf_url"),
                "published": paper.get("published"),
                "summary": f"阅读失败: {str(e)}",
                "key_contributions": [],
                "methods": [],
                "experiments": [],
                "limitations": [],
                "relevance_score": 0,
                "relevance_reason": "阅读失败"
            }

    def _format_paper_for_reading(self, paper: Dict[str, Any]) -> str:
        """将论文信息格式化为阅读文本

        Args:
            paper: 论文信息字典

        Returns:
            格式化后的文本
        """
        lines = [
            f"标题: {paper.get('title', 'N/A')}",
            f"作者: {', '.join(paper.get('authors', []))}",
            f"arXiv ID: {paper.get('arxiv_id', 'N/A')}",
            f"发布时间: {paper.get('published', 'N/A')}",
            "",
            "摘要:",
            paper.get('abstract', 'N/A'),
        ]
        return "\n".join(lines)

    def _parse_summary_response(self, content: str) -> Dict[str, Any]:
        """解析摘要响应JSON

        Args:
            content: LLM响应内容

        Returns:
            摘要数据字典
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

        raise ValueError(f"无法解析摘要响应: {content[:200]}...")

    async def read_single_paper(
        self,
        title: str,
        authors: List[str],
        abstract: str,
        arxiv_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """独立阅读单篇论文（不依赖state）

        Args:
            title: 论文标题
            authors: 作者列表
            abstract: 论文摘要
            arxiv_id: arXiv ID
            **kwargs: 其他论文信息

        Returns:
            论文摘要字典
        """
        paper = {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "arxiv_id": arxiv_id,
            **kwargs
        }
        return await self._read_paper(paper)

    def format_summary(self, summary: Dict[str, Any]) -> str:
        """格式化论文摘要为可读文本

        Args:
            summary: 论文摘要字典

        Returns:
            格式化后的文本
        """
        lines = [
            f"# {summary.get('title', 'N/A')}",
            "",
            f"**作者**: {', '.join(summary.get('authors', [])[:3])}",
            f"**arXiv**: {summary.get('arxiv_id', 'N/A')}",
            f"**相关度**: {summary.get('relevance_score', 'N/A')}/10",
            "",
            "## 概述",
            summary.get('summary', 'N/A'),
            "",
            "## 核心贡献",
        ]

        for contrib in summary.get('key_contributions', []):
            lines.append(f"- {contrib}")

        lines.extend(["", "## 研究方法"])
        for method in summary.get('methods', []):
            lines.append(f"- {method}")

        lines.extend(["", "## 实验结果"])
        for exp in summary.get('experiments', []):
            lines.append(f"- {exp}")

        if summary.get('limitations'):
            lines.extend(["", "## 局限性"])
            for lim in summary.get('limitations', []):
                lines.append(f"- {lim}")

        lines.extend([
            "",
            f"**相关度说明**: {summary.get('relevance_reason', 'N/A')}",
            f"**链接**: {summary.get('url', 'N/A')}"
        ])

        return "\n".join(lines)

    def format_summaries(self, summaries: List[Dict[str, Any]]) -> str:
        """格式化多篇论文摘要

        Args:
            summaries: 论文摘要列表

        Returns:
            格式化后的文本
        """
        if not summaries:
            return "没有论文摘要。"

        sections = [f"# 论文阅读总结\n共{len(summaries)}篇论文\n"]

        for i, summary in enumerate(summaries, 1):
            sections.append(f"## [{i}] {summary.get('title', 'N/A')}")
            sections.append(f"**相关度**: {summary.get('relevance_score', 'N/A')}/10")
            sections.append(f"**核心贡献**: {', '.join(summary.get('key_contributions', [])[:2])}")
            sections.append("")

        return "\n".join(sections)
