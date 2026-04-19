"""Analyst Agent - 多论文对比分析"""
import json
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base import BaseAgent
from utils.llm import create_llm
from utils.state import add_message
from utils.logger import logger


class AnalystAgent(BaseAgent):
    """Analyst Agent负责对多篇论文进行横向对比分析

    职责：
    1. 对比不同论文的方法和技术路线
    2. 分析各方法的优缺点和适用场景
    3. 识别论文间的关联和演进关系
    4. 总结领域发展趋势和研究热点
    5. 生成结构化的对比分析报告
    """

    def __init__(self, llm=None):
        super().__init__(name="Analyst", llm=llm)
        if self.llm is None:
            self.llm = create_llm()
        self._load_prompt()

    def _load_prompt(self) -> None:
        """加载Analyst的系统Prompt"""
        try:
            with open("prompts/analyst.txt", "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            self.system_prompt = self._get_default_prompt()
            logger.warning("analyst.txt not found, using default prompt")

    def _get_default_prompt(self) -> str:
        """获取默认的系统Prompt"""
        return """你是一个专业的学术研究分析师。你的职责是对多篇学术论文进行深入的横向对比分析。

## 核心职责
1. 对比不同论文的研究方法和技术路线
2. 分析各方法的优缺点和适用场景
3. 识别论文间的关联、差异和演进关系
4. 总结领域发展趋势和未来方向

## 分析维度

1. **方法对比 (Method Comparison)**
   - 各论文采用了什么核心方法？
   - 方法之间的主要差异是什么？
   - 各方法的优势和局限性？

2. **技术路线对比 (Technical Approach)**
   - 技术架构有何不同？
   - 关键创新点对比？
   - 实现复杂度评估？

3. **性能对比 (Performance Comparison)**
   - 实验结果横向对比？
   - 各方法的适用场景？
   - 效果与成本的权衡？

4. **发展趋势 (Trends)**
   - 该领域的演进方向？
   - 研究热点和空白？
   - 未来可能的发展方向？

## 输出格式
你必须以JSON格式输出，格式如下：
{
    "overview": "领域概述和研究背景",
    "method_comparison": [
        {"paper": "论文标题", "method": "方法描述", "pros": "优势", "cons": "局限"}
    ],
    "key_insights": ["洞察1", "洞察2", "洞察3"],
    "trends": ["趋势1", "趋势2"],
    "recommendations": ["建议1", "建议2"]
}

请确保输出是有效的JSON格式。"""

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行Analyst任务

        Args:
            state: 当前状态，包含paper_summaries

        Returns:
            更新后的状态，包含analysis
        """
        summaries = state.get("paper_summaries", [])
        if not summaries:
            logger.warning("Analyst: 没有论文摘要需要分析")
            add_message(state, "Analyst", "没有论文摘要需要分析")
            state["analysis"] = {"error": "没有论文摘要"}
            state["current_step"] = "analysis_completed"
            return state

        logger.info(f"Analyst开始分析{len(summaries)}篇论文...")
        add_message(state, "Analyst", f"开始分析{len(summaries)}篇论文")

        try:
            # 构建分析文本
            analysis_text = self._format_summaries_for_analysis(summaries)

            # 构建消息
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"请对以下论文进行横向对比分析：\n\n{analysis_text}")
            ]

            # 调用LLM生成分析
            response = await self.llm.ainvoke(messages)
            content = response.content

            # 解析JSON响应
            analysis_data = self._parse_analysis_response(content)

            # 更新状态
            state["analysis"] = analysis_data
            state["current_step"] = "analysis_completed"

            # 添加日志
            add_message(state, "Analyst", f"完成{len(summaries)}篇论文的对比分析")

            # 记录到记忆
            self.add_to_memory("system", self.system_prompt)
            self.add_to_memory("user", f"分析了{len(summaries)}篇论文")
            self.add_to_memory("assistant", "生成对比分析报告")

            logger.info(f"Analyst完成分析，生成对比报告")

            return state

        except Exception as e:
            error_msg = f"Analyst执行失败: {str(e)}"
            logger.error(error_msg)
            add_message(state, "Analyst", error_msg)
            state["current_step"] = "analysis_failed"
            raise

    def _format_summaries_for_analysis(self, summaries: List[Dict[str, Any]]) -> str:
        """将论文摘要格式化为分析文本

        Args:
            summaries: 论文摘要列表

        Returns:
            格式化后的文本
        """
        lines = [f"共{len(summaries)}篇论文需要对比分析：\n"]

        for i, summary in enumerate(summaries, 1):
            lines.append(f"## 论文{i}: {summary.get('title', 'N/A')}")
            lines.append(f"**arXiv ID**: {summary.get('arxiv_id', 'N/A')}")
            lines.append(f"**相关度**: {summary.get('relevance_score', 'N/A')}/10")
            lines.append("")
            lines.append("**概述**:")
            lines.append(summary.get('summary', 'N/A'))
            lines.append("")

            if summary.get('key_contributions'):
                lines.append("**核心贡献**:")
                for contrib in summary.get('key_contributions', []):
                    lines.append(f"- {contrib}")
                lines.append("")

            if summary.get('methods'):
                lines.append("**研究方法**:")
                for method in summary.get('methods', []):
                    lines.append(f"- {method}")
                lines.append("")

            if summary.get('experiments'):
                lines.append("**实验结果**:")
                for exp in summary.get('experiments', []):
                    lines.append(f"- {exp}")
                lines.append("")

            if summary.get('limitations'):
                lines.append("**局限性**:")
                for lim in summary.get('limitations', []):
                    lines.append(f"- {lim}")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines)

    def _parse_analysis_response(self, content: str) -> Dict[str, Any]:
        """解析分析响应JSON

        Args:
            content: LLM响应内容

        Returns:
            分析数据字典
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

        # 尝试从文本中提取JSON（处理可能的截断情况）
        try:
            start_idx = content.find("{")
            end_idx = content.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx+1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 尝试修复常见的JSON截断问题并提取
        try:
            start_idx = content.find("{")
            if start_idx != -1:
                json_str = content[start_idx:]
                # 尝试找到最后一个完整的JSON对象
                # 通过查找最后一个双引号后的闭合括号
                last_brace = json_str.rfind("}")
                if last_brace > 0:
                    # 尝试逐步缩短字符串直到可以解析
                    for end_idx in range(last_brace + 1, len(json_str) + 1):
                        try:
                            candidate = json_str[:end_idx]
                            result = json.loads(candidate)
                            logger.warning(f"JSON响应被截断，已尝试修复并提取有效部分")
                            return result
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        # 如果所有解析方法都失败，返回一个包含原始内容的错误结构
        logger.error(f"无法解析分析响应，返回默认结构。原始内容前500字符: {content[:500]}")
        return {
            "overview": f"解析分析响应时出错。原始响应内容（前300字符）：{content[:300]}...",
            "method_comparison": [],
            "technical_matrix": {"dimensions": [], "comparisons": "解析失败"},
            "performance_analysis": "解析失败",
            "key_insights": ["分析响应解析失败，请检查LLM输出"],
            "trends": [],
            "recommendations": [],
            "_parse_error": True,
            "_raw_content_preview": content[:500]
        }

    async def analyze_papers(
        self,
        summaries: List[Dict[str, Any]],
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """独立分析多篇论文（不依赖state）

        Args:
            summaries: 论文摘要列表
            query: 研究问题（可选）

        Returns:
            分析结果字典
        """
        if not summaries:
            return {"error": "没有论文摘要"}

        # 构建分析文本
        analysis_text = self._format_summaries_for_analysis(summaries)

        if query:
            analysis_text = f"研究问题: {query}\n\n{analysis_text}"

        # 构建消息
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请对以下论文进行横向对比分析：\n\n{analysis_text}")
        ]

        # 调用LLM生成分析
        response = await self.llm.ainvoke(messages)
        content = response.content

        # 解析JSON响应
        return self._parse_analysis_response(content)

    def format_analysis(self, analysis: Dict[str, Any]) -> str:
        """格式化分析结果为可读文本

        Args:
            analysis: 分析结果字典

        Returns:
            格式化后的文本
        """
        lines = ["# 论文对比分析报告\n"]

        # 概述
        if analysis.get('overview'):
            lines.extend(["## 领域概述", analysis['overview'], ""])

        # 方法对比
        if analysis.get('method_comparison'):
            lines.extend(["## 方法对比", ""])
            for item in analysis['method_comparison']:
                lines.append(f"### {item.get('paper', 'N/A')}")
                lines.append(f"**方法**: {item.get('method', 'N/A')}")
                lines.append(f"**优势**: {item.get('pros', 'N/A')}")
                lines.append(f"**局限**: {item.get('cons', 'N/A')}")
                lines.append("")

        # 关键洞察
        if analysis.get('key_insights'):
            lines.extend(["## 关键洞察", ""])
            for i, insight in enumerate(analysis['key_insights'], 1):
                lines.append(f"{i}. {insight}")
            lines.append("")

        # 发展趋势
        if analysis.get('trends'):
            lines.extend(["## 发展趋势", ""])
            for i, trend in enumerate(analysis['trends'], 1):
                lines.append(f"{i}. {trend}")
            lines.append("")

        # 建议
        if analysis.get('recommendations'):
            lines.extend(["## 研究建议", ""])
            for i, rec in enumerate(analysis['recommendations'], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return "\n".join(lines)

    def get_top_papers(
        self,
        summaries: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """获取相关度最高的论文

        Args:
            summaries: 论文摘要列表
            top_k: 返回前几篇

        Returns:
            排序后的论文列表
        """
        # 按相关度排序
        sorted_summaries = sorted(
            summaries,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )
        return sorted_summaries[:top_k]

    def group_by_method(
        self,
        summaries: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按方法类型对论文进行分组

        Args:
            summaries: 论文摘要列表

        Returns:
            按方法分组的字典
        """
        groups = {}

        for summary in summaries:
            methods = summary.get('methods', [])
            if methods:
                # 使用第一个方法作为分组依据
                method_key = methods[0].split(':')[0][:30]  # 简化方法名
                if method_key not in groups:
                    groups[method_key] = []
                groups[method_key].append(summary)
            else:
                if '其他' not in groups:
                    groups['其他'] = []
                groups['其他'].append(summary)

        return groups
