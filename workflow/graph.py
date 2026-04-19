"""LangGraph工作流定义 - 多Agent协作流程"""
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import asyncio

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents import PlannerAgent, SearcherAgent, ReaderAgent, AnalystAgent, WriterAgent
from utils.state import ResearchState, create_initial_state, add_message
from utils.logger import logger


class ResearchWorkflow:
    """研究工作流 - 使用LangGraph编排多Agent协作

    工作流节点：
    1. planner - 任务规划
    2. searcher - 论文检索
    3. reader - 论文阅读
    4. analyst - 对比分析
    5. writer - 报告生成

    流程：
    init -> planner -> searcher -> reader -> analyst -> writer -> END
    """

    def __init__(
        self,
        planner: Optional[PlannerAgent] = None,
        searcher: Optional[SearcherAgent] = None,
        reader: Optional[ReaderAgent] = None,
        analyst: Optional[AnalystAgent] = None,
        writer: Optional[WriterAgent] = None,
    ):
        """初始化工作流

        Args:
            planner: Planner Agent实例
            searcher: Searcher Agent实例
            reader: Reader Agent实例
            analyst: Analyst Agent实例
            writer: Writer Agent实例
        """
        # 初始化Agent（如果未提供则创建新实例）
        self.planner = planner or PlannerAgent()
        self.searcher = searcher or SearcherAgent()
        self.reader = reader or ReaderAgent()
        self.analyst = analyst or AnalystAgent()
        self.writer = writer or WriterAgent()

        # 构建工作流图
        self.graph = self._build_graph()

        logger.info("ResearchWorkflow initialized")

    def _build_graph(self) -> StateGraph:
        """构建LangGraph工作流图

        Returns:
            编译后的StateGraph
        """
        # 定义状态图
        workflow = StateGraph(ResearchState)

        # 添加节点
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("searcher", self._searcher_node)
        workflow.add_node("reader", self._reader_node)
        workflow.add_node("analyst", self._analyst_node)
        workflow.add_node("writer", self._writer_node)

        # 添加边 - 定义流程
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "searcher")
        workflow.add_edge("searcher", "reader")
        workflow.add_edge("reader", "analyst")
        workflow.add_edge("analyst", "writer")
        workflow.add_edge("writer", END)

        # 编译图
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    async def _planner_node(self, state: ResearchState) -> ResearchState:
        """Planner节点 - 任务规划

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("Workflow: Executing Planner node")
        try:
            state = await self.planner.execute(state)
            return state
        except Exception as e:
            logger.error(f"Planner node failed: {e}")
            add_message(state, "Workflow", f"Planner执行失败: {e}")
            state["current_step"] = "planner_failed"
            raise

    async def _searcher_node(self, state: ResearchState) -> ResearchState:
        """Searcher节点 - 论文检索

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("Workflow: Executing Searcher node")
        try:
            state = await self.searcher.execute(state)
            return state
        except Exception as e:
            logger.error(f"Searcher node failed: {e}")
            add_message(state, "Workflow", f"Searcher执行失败: {e}")
            state["current_step"] = "searcher_failed"
            raise

    async def _reader_node(self, state: ResearchState) -> ResearchState:
        """Reader节点 - 论文阅读

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("Workflow: Executing Reader node")
        try:
            state = await self.reader.execute(state)
            return state
        except Exception as e:
            logger.error(f"Reader node failed: {e}")
            add_message(state, "Workflow", f"Reader执行失败: {e}")
            state["current_step"] = "reader_failed"
            raise

    async def _analyst_node(self, state: ResearchState) -> ResearchState:
        """Analyst节点 - 对比分析

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("Workflow: Executing Analyst node")
        try:
            state = await self.analyst.execute(state)
            return state
        except Exception as e:
            logger.error(f"Analyst node failed: {e}")
            add_message(state, "Workflow", f"Analyst执行失败: {e}")
            state["current_step"] = "analyst_failed"
            raise

    async def _writer_node(self, state: ResearchState) -> ResearchState:
        """Writer节点 - 报告生成

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("Workflow: Executing Writer node")
        try:
            state = await self.writer.execute(state)
            return state
        except Exception as e:
            logger.error(f"Writer node failed: {e}")
            add_message(state, "Workflow", f"Writer执行失败: {e}")
            state["current_step"] = "writer_failed"
            raise

    async def run(
        self,
        query: str,
        max_papers: int = 10,
        config: Optional[Dict[str, Any]] = None
    ) -> ResearchState:
        """运行完整工作流

        Args:
            query: 研究问题
            max_papers: 最大阅读论文数量，默认10篇
            config: 运行配置（可选）

        Returns:
            最终状态
        """
        logger.info(f"Workflow: Starting research for query: {query[:50]}...")
        logger.info(f"Workflow: Max papers to read: {max_papers}")

        # 创建初始状态
        initial_state = create_initial_state(query, max_papers=max_papers)

        # 默认配置
        if config is None:
            config = {"configurable": {"thread_id": f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}}

        try:
            # 执行工作流
            result = await self.graph.ainvoke(initial_state, config)
            logger.info("Workflow: Research completed successfully")
            return result

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            initial_state["errors"].append({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            initial_state["current_step"] = "workflow_failed"
            raise

    async def run_step_by_step(
        self,
        query: str,
        max_papers: int = 10,
        callback: Optional[Callable[[str, ResearchState], None]] = None
    ) -> ResearchState:
        """逐步运行工作流，支持回调函数

        Args:
            query: 研究问题
            max_papers: 最大阅读论文数量，默认10篇
            callback: 回调函数，接收(step_name, state)

        Returns:
            最终状态
        """
        logger.info(f"Workflow: Starting step-by-step research for: {query[:50]}...")

        state = create_initial_state(query, max_papers=max_papers)
        steps = [
            ("planner", self._planner_node),
            ("searcher", self._searcher_node),
            ("reader", self._reader_node),
            ("analyst", self._analyst_node),
            ("writer", self._writer_node),
        ]

        for step_name, step_func in steps:
            logger.info(f"Workflow: Executing step '{step_name}'")

            try:
                state = await step_func(state)

                # 调用回调函数
                if callback:
                    callback(step_name, state)

            except Exception as e:
                logger.error(f"Workflow step '{step_name}' failed: {e}")
                state["errors"].append({
                    "error": f"Step {step_name} failed: {e}",
                    "timestamp": datetime.now().isoformat()
                })
                raise

        logger.info("Workflow: Step-by-step research completed")
        return state

    def get_workflow_diagram(self) -> str:
        """获取工作流图描述

        Returns:
            Mermaid格式的流程图
        """
        return """
```mermaid
graph TD
    A[用户输入研究问题] --> B[Planner<br/>任务规划]
    B --> C[Searcher<br/>论文检索]
    C --> D[Reader<br/>论文阅读]
    D --> E[Analyst<br/>对比分析]
    E --> F[Writer<br/>报告生成]
    F --> G[输出综述报告]

    style A fill:#e1f5fe
    style G fill:#c8e6c9
```
"""

    def get_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        """获取执行摘要

        Args:
            state: 最终状态

        Returns:
            执行摘要字典
        """
        start_time = state.get("start_time")
        end_time = state.get("end_time")

        duration = None
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()

        return {
            "query": state.get("query", ""),
            "status": state.get("current_step", "unknown"),
            "duration_seconds": duration,
            "papers_found": len(state.get("papers", [])),
            "papers_summarized": len(state.get("paper_summaries", [])),
            "has_analysis": bool(state.get("analysis")),
            "has_report": bool(state.get("report")),
            "message_count": len(state.get("messages", [])),
            "error_count": len(state.get("errors", [])),
        }


# 便捷函数
async def run_research(
    query: str,
    planner: Optional[PlannerAgent] = None,
    searcher: Optional[SearcherAgent] = None,
    reader: Optional[ReaderAgent] = None,
    analyst: Optional[AnalystAgent] = None,
    writer: Optional[WriterAgent] = None,
) -> ResearchState:
    """便捷函数：运行完整研究流程

    Args:
        query: 研究问题
        planner: Planner Agent（可选）
        searcher: Searcher Agent（可选）
        reader: Reader Agent（可选）
        analyst: Analyst Agent（可选）
        writer: Writer Agent（可选）

    Returns:
        最终状态
    """
    workflow = ResearchWorkflow(
        planner=planner,
        searcher=searcher,
        reader=reader,
        analyst=analyst,
        writer=writer,
    )
    return await workflow.run(query)
