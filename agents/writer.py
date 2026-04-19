"""Writer Agent - 结构化报告生成"""
import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base import BaseAgent
from utils.llm import create_llm
from utils.state import add_message
from utils.logger import logger


class WriterAgent(BaseAgent):
    """Writer Agent负责生成结构化的综述报告

    职责：
    1. 整合所有Agent的分析结果
    2. 生成结构化的综述报告
    3. 确保报告逻辑清晰、内容完整
    4. 提供报告导出功能
    """

    def __init__(self, llm=None):
        super().__init__(name="Writer", llm=llm)
        if self.llm is None:
            self.llm = create_llm()
        self._load_prompt()

    def _load_prompt(self) -> None:
        """加载Writer的系统Prompt"""
        try:
            with open("prompts/writer.txt", "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            self.system_prompt = self._get_default_prompt()
            logger.warning("writer.txt not found, using default prompt")

    def _get_default_prompt(self) -> str:
        """获取默认的系统Prompt"""
        return """你是一个专业的学术报告撰写专家。你的职责是根据多Agent协作的分析结果，生成一份结构化的综述报告。

## 核心职责
1. 整合Planner的任务规划、Searcher的检索结果、Reader的论文摘要、Analyst的对比分析
2. 生成逻辑清晰、内容完整的综述报告
3. 确保报告具有学术规范性和可读性

## 报告结构

1. **摘要 (Abstract)**
   - 研究背景和目的
   - 主要发现（2-3句话概括）

2. **引言 (Introduction)**
   - 研究背景和动机
   - 研究问题和范围
   - 报告结构说明

3. **方法概述 (Methodology Overview)**
   - 调研方法说明
   - 文献检索策略
   - 分析框架

4. **主要发现 (Key Findings)**
   - 核心论文介绍
   - 方法对比总结
   - 关键洞察

5. **讨论 (Discussion)**
   - 领域发展趋势
   - 研究热点和空白
   - 方法选择的考量

6. **结论 (Conclusion)**
   - 主要结论总结
   - 研究建议
   - 未来展望

7. **参考文献 (References)**
   - 引用的论文列表

## 输出格式
直接输出Markdown格式的报告，不需要JSON格式。

## 写作要求
1. 语言专业、客观、准确
2. 逻辑清晰，层次分明
3. 引用具体论文支撑观点
4. 报告长度适中（2000-4000字）"""

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行Writer任务

        Args:
            state: 当前状态，包含query、papers、paper_summaries、analysis

        Returns:
            更新后的状态，包含report
        """
        query = state.get("query", "")
        papers = state.get("papers", [])
        summaries = state.get("paper_summaries", [])
        analysis = state.get("analysis", {})

        logger.info(f"Writer开始生成报告: {query[:50]}...")
        add_message(state, "Writer", f"开始生成综述报告: {query}")

        try:
            # 构建报告输入
            report_input = self._build_report_input(
                query=query,
                papers=papers,
                summaries=summaries,
                analysis=analysis
            )

            # 构建消息
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=report_input)
            ]

            # 调用LLM生成报告（带超时保护）
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke(messages),
                    timeout=300  # 5分钟超时
                )
            except asyncio.TimeoutError:
                raise TimeoutError("Writer LLM调用超时（5分钟），请检查网络连接或API服务状态")
            report_content = response.content

            # 更新状态
            state["report"] = report_content
            state["current_step"] = "report_completed"
            state["end_time"] = datetime.now()

            # 添加日志
            add_message(state, "Writer", "综述报告生成完成")

            # 记录到记忆
            self.add_to_memory("system", self.system_prompt)
            self.add_to_memory("user", f"生成关于'{query}'的报告")
            self.add_to_memory("assistant", f"报告已生成，长度{len(report_content)}字符")

            logger.info(f"Writer完成报告生成，长度{len(report_content)}字符")

            return state

        except Exception as e:
            error_msg = f"Writer执行失败: {str(e)}"
            logger.error(error_msg)
            add_message(state, "Writer", error_msg)
            state["current_step"] = "report_failed"
            raise

    def _build_report_input(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> str:
        """构建报告生成的输入文本

        Args:
            query: 研究问题
            papers: 检索到的论文列表
            summaries: 论文摘要列表
            analysis: 分析结果

        Returns:
            格式化的输入文本
        """
        lines = [f"# 研究问题\n{query}\n"]

        # 添加论文信息
        lines.append(f"## 检索到的论文（共{len(papers)}篇）\n")
        for i, paper in enumerate(papers, 1):
            lines.append(f"{i}. **{paper.get('title', 'N/A')}**")
            lines.append(f"   - 作者: {', '.join(paper.get('authors', [])[:3])}")
            lines.append(f"   - arXiv: {paper.get('arxiv_id', 'N/A')}")
            lines.append(f"   - 链接: {paper.get('url', 'N/A')}")
            lines.append("")

        # 添加论文摘要
        lines.append(f"## 论文摘要\n")
        for i, summary in enumerate(summaries, 1):
            lines.append(f"### 论文{i}: {summary.get('title', 'N/A')}")
            lines.append(f"**相关度**: {summary.get('relevance_score', 'N/A')}/10")
            lines.append(f"**概述**: {summary.get('summary', 'N/A')[:200]}...")

            if summary.get('key_contributions'):
                lines.append(f"**核心贡献**: {', '.join(summary.get('key_contributions', [])[:2])}")

            if summary.get('methods'):
                lines.append(f"**方法**: {', '.join(summary.get('methods', [])[:2])}")

            lines.append("")

        # 添加分析结果
        if analysis:
            lines.append("## 对比分析结果\n")

            if analysis.get('overview'):
                lines.append(f"**领域概述**: {analysis['overview']}\n")

            if analysis.get('method_comparison'):
                lines.append("**方法对比**:")
                for item in analysis['method_comparison'][:5]:  # 限制数量
                    lines.append(f"- {item.get('paper', 'N/A')}: {item.get('method', 'N/A')}")
                lines.append("")

            if analysis.get('key_insights'):
                lines.append("**关键洞察**:")
                for insight in analysis['key_insights']:
                    lines.append(f"- {insight}")
                lines.append("")

            if analysis.get('trends'):
                lines.append("**发展趋势**:")
                for trend in analysis['trends']:
                    lines.append(f"- {trend}")
                lines.append("")

            if analysis.get('recommendations'):
                lines.append("**研究建议**:")
                for rec in analysis['recommendations']:
                    lines.append(f"- {rec}")
                lines.append("")

        lines.append("---\n")
        lines.append("请根据以上信息生成一份结构化的综述报告。")

        return "\n".join(lines)

    async def generate_report(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> str:
        """独立生成报告（不依赖state）

        Args:
            query: 研究问题
            papers: 论文列表
            summaries: 论文摘要列表
            analysis: 分析结果

        Returns:
            报告内容
        """
        # 构建报告输入
        report_input = self._build_report_input(query, papers, summaries, analysis)

        # 构建消息
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=report_input)
        ]

        # 调用LLM生成报告
        response = await self.llm.ainvoke(messages)
        return response.content

    def save_report(
        self,
        report: str,
        filename: Optional[str] = None,
        output_dir: str = "./reports"
    ) -> str:
        """保存报告到文件

        Args:
            report: 报告内容
            filename: 文件名（可选）
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        import os

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"research_report_{timestamp}.md"

        filepath = os.path.join(output_dir, filename)

        # 保存文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"报告已保存到: {filepath}")
        return filepath

    def generate_report_metadata(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成报告元数据

        Args:
            query: 研究问题
            papers: 论文列表
            summaries: 论文摘要列表
            analysis: 分析结果

        Returns:
            元数据字典
        """
        # 计算平均相关度
        avg_relevance = 0
        if summaries:
            scores = [s.get('relevance_score', 0) for s in summaries]
            avg_relevance = sum(scores) / len(scores)

        # 统计方法类型
        methods = set()
        for summary in summaries:
            for method in summary.get('methods', []):
                methods.add(method.split(':')[0])

        return {
            "title": f"Research Report: {query}",
            "query": query,
            "generated_at": datetime.now().isoformat(),
            "statistics": {
                "total_papers": len(papers),
                "summarized_papers": len(summaries),
                "avg_relevance_score": round(avg_relevance, 2),
                "method_types": list(methods),
            },
            "top_papers": [
                {
                    "title": s.get('title'),
                    "arxiv_id": s.get('arxiv_id'),
                    "relevance_score": s.get('relevance_score')
                }
                for s in sorted(
                    summaries,
                    key=lambda x: x.get('relevance_score', 0),
                    reverse=True
                )[:5]
            ]
        }

    def format_report_with_metadata(
        self,
        report: str,
        metadata: Dict[str, Any]
    ) -> str:
        """将元数据添加到报告头部

        Args:
            report: 报告内容
            metadata: 元数据

        Returns:
            完整的报告
        """
        header_lines = [
            "---",
            f"title: {metadata.get('title', 'Research Report')}",
            f"date: {metadata.get('generated_at', '')}",
            f"papers_analyzed: {metadata.get('statistics', {}).get('total_papers', 0)}",
            "---",
            "",
        ]

        # 添加统计信息
        stats = metadata.get('statistics', {})
        header_lines.extend([
            "## 报告信息",
            f"- **研究问题**: {metadata.get('query', 'N/A')}",
            f"- **分析论文数**: {stats.get('total_papers', 0)}",
            f"- **平均相关度**: {stats.get('avg_relevance_score', 0)}/10",
            f"- **方法类型**: {', '.join(stats.get('method_types', []))}",
            "",
            "---",
            "",
        ])

        return "\n".join(header_lines) + report
