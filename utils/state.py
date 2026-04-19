"""状态管理模块"""
import json
import os
from typing import Any, Dict, List, Optional, TypedDict, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


class ResearchState(TypedDict, total=False):
    """研究工作流状态定义

    用于LangGraph状态传递
    """
    # 输入
    query: str  # 用户研究问题
    max_papers: int  # 最大阅读论文数量

    # Planner输出
    sub_tasks: List[Dict[str, Any]]  # 子任务列表

    # Searcher输出
    papers: List[Dict[str, Any]]  # 检索到的论文列表

    # Reader输出
    paper_summaries: List[Dict[str, Any]]  # 论文摘要列表

    # Analyst输出
    analysis: Dict[str, Any]  # 对比分析结果

    # Writer输出
    report: str  # 最终报告

    # 元数据
    current_step: str  # 当前执行步骤
    messages: List[Dict[str, str]]  # 执行日志
    errors: List[str]  # 错误记录
    start_time: Optional[datetime]  # 开始时间
    end_time: Optional[datetime]  # 结束时间


@dataclass
class PaperInfo:
    """论文信息数据结构"""
    title: str
    authors: List[str]
    abstract: str
    url: str
    pdf_url: Optional[str] = None
    published: Optional[str] = None
    arxiv_id: Optional[str] = None
    summary: Optional[str] = None  # Reader生成的摘要
    key_contributions: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    experiments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "published": self.published,
            "arxiv_id": self.arxiv_id,
            "summary": self.summary,
            "key_contributions": self.key_contributions,
            "methods": self.methods,
            "experiments": self.experiments,
        }


@dataclass
class SubTask:
    """子任务数据结构"""
    id: str
    description: str
    agent_type: str  # 'searcher', 'reader', 'analyst'
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Any] = None
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status,
            "result": self.result,
            "dependencies": self.dependencies,
        }


def create_initial_state(query: str, max_papers: int = 10) -> ResearchState:
    """创建初始状态

    Args:
        query: 用户研究问题
        max_papers: 最大阅读论文数量，默认10篇

    Returns:
        初始研究状态
    """
    return {
        "query": query,
        "max_papers": max_papers,
        "sub_tasks": [],
        "papers": [],
        "paper_summaries": [],
        "analysis": {},
        "report": "",
        "current_step": "init",
        "messages": [],
        "errors": [],
        "start_time": datetime.now(),
        "end_time": None,
    }


def add_message(state: ResearchState, agent: str, message: str) -> None:
    """向状态中添加日志消息"""
    if "messages" not in state:
        state["messages"] = []
    state["messages"].append({
        "agent": agent,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    })


def add_error(state: ResearchState, error: str) -> None:
    """向状态中添加错误记录"""
    if "errors" not in state:
        state["errors"] = []
    state["errors"].append({
        "error": error,
        "timestamp": datetime.now().isoformat(),
    })


class StateManager:
    """状态管理器 - 提供状态的持久化、快照和恢复功能"""

    def __init__(self, storage_dir: str = "./state_storage"):
        """初始化状态管理器

        Args:
            storage_dir: 状态存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_state(
        self,
        state: ResearchState,
        session_id: Optional[str] = None
    ) -> str:
        """保存状态到文件

        Args:
            state: 研究状态
            session_id: 会话ID（可选，默认使用时间戳）

        Returns:
            保存的文件路径
        """
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        filepath = self.storage_dir / f"state_{session_id}.json"

        # 序列化状态
        state_dict = self._serialize_state(state)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)

        return str(filepath)

    def load_state(self, session_id: str) -> Optional[ResearchState]:
        """从文件加载状态

        Args:
            session_id: 会话ID

        Returns:
            研究状态，如果文件不存在返回None
        """
        filepath = self.storage_dir / f"state_{session_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            state_dict = json.load(f)

        return self._deserialize_state(state_dict)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有保存的会话

        Returns:
            会话信息列表
        """
        sessions = []

        for filepath in self.storage_dir.glob("state_*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    state_dict = json.load(f)

                session_info = {
                    "session_id": filepath.stem.replace("state_", ""),
                    "query": state_dict.get("query", "N/A"),
                    "current_step": state_dict.get("current_step", "unknown"),
                    "created_at": state_dict.get("start_time", "N/A"),
                    "filepath": str(filepath),
                }
                sessions.append(session_info)
            except Exception:
                continue

        # 按时间排序
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        return sessions

    def delete_state(self, session_id: str) -> bool:
        """删除保存的状态

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        filepath = self.storage_dir / f"state_{session_id}.json"

        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def create_snapshot(
        self,
        state: ResearchState,
        snapshot_name: Optional[str] = None
    ) -> str:
        """创建状态快照

        Args:
            state: 研究状态
            snapshot_name: 快照名称（可选）

        Returns:
            快照文件路径
        """
        if snapshot_name is None:
            step = state.get("current_step", "unknown")
            timestamp = datetime.now().strftime("%H%M%S")
            snapshot_name = f"{step}_{timestamp}"

        snapshot_dir = self.storage_dir / "snapshots"
        snapshot_dir.mkdir(exist_ok=True)

        filepath = snapshot_dir / f"snapshot_{snapshot_name}.json"

        state_dict = self._serialize_state(state)
        state_dict["_snapshot_info"] = {
            "name": snapshot_name,
            "created_at": datetime.now().isoformat(),
            "step": state.get("current_step"),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)

        return str(filepath)

    def restore_snapshot(self, snapshot_name: str) -> Optional[ResearchState]:
        """恢复快照

        Args:
            snapshot_name: 快照名称

        Returns:
            研究状态，如果不存在返回None
        """
        snapshot_dir = self.storage_dir / "snapshots"
        filepath = snapshot_dir / f"snapshot_{snapshot_name}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            state_dict = json.load(f)

        # 移除快照元数据
        state_dict.pop("_snapshot_info", None)

        return self._deserialize_state(state_dict)

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """列出所有快照

        Returns:
            快照信息列表
        """
        snapshot_dir = self.storage_dir / "snapshots"
        snapshots = []

        if not snapshot_dir.exists():
            return snapshots

        for filepath in snapshot_dir.glob("snapshot_*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    state_dict = json.load(f)

                info = state_dict.get("_snapshot_info", {})
                snapshots.append({
                    "name": info.get("name", filepath.stem),
                    "step": info.get("step", "unknown"),
                    "created_at": info.get("created_at", "N/A"),
                    "filepath": str(filepath),
                })
            except Exception:
                continue

        snapshots.sort(key=lambda x: x["created_at"], reverse=True)
        return snapshots

    def _serialize_state(self, state: ResearchState) -> Dict[str, Any]:
        """序列化状态

        Args:
            state: 研究状态

        Returns:
            可JSON序列化的字典
        """
        state_dict = dict(state)

        # 处理datetime对象
        for key in ["start_time", "end_time"]:
            if key in state_dict and isinstance(state_dict[key], datetime):
                state_dict[key] = state_dict[key].isoformat()

        return state_dict

    def _deserialize_state(self, state_dict: Dict[str, Any]) -> ResearchState:
        """反序列化状态

        Args:
            state_dict: 状态字典

        Returns:
            研究状态
        """
        # 处理datetime字符串
        for key in ["start_time", "end_time"]:
            if key in state_dict and isinstance(state_dict[key], str):
                try:
                    state_dict[key] = datetime.fromisoformat(state_dict[key])
                except ValueError:
                    pass

        return state_dict


class StateValidator:
    """状态验证器 - 验证状态的完整性和一致性"""

    @staticmethod
    def validate_state(state: ResearchState) -> List[str]:
        """验证状态

        Args:
            state: 研究状态

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 检查必需字段
        if "query" not in state or not state["query"]:
            errors.append("缺少必需的'query'字段")

        # 检查数据类型
        if "papers" in state and not isinstance(state["papers"], list):
            errors.append("'papers'必须是列表类型")

        if "paper_summaries" in state and not isinstance(state["paper_summaries"], list):
            errors.append("'paper_summaries'必须是列表类型")

        # 检查一致性
        papers_count = len(state.get("papers", []))
        summaries_count = len(state.get("paper_summaries", []))

        if summaries_count > papers_count:
            errors.append(f"摘要数量({summaries_count})超过论文数量({papers_count})")

        # 检查状态流转
        current_step = state.get("current_step", "")
        valid_steps = [
            "init", "planning_completed", "planning_failed",
            "search_completed", "search_failed",
            "reading_completed", "reading_failed",
            "analysis_completed", "analysis_failed",
            "report_completed", "report_failed",
            "workflow_failed"
        ]

        if current_step and current_step not in valid_steps:
            errors.append(f"未知的current_step: {current_step}")

        return errors

    @staticmethod
    def is_state_complete(state: ResearchState) -> bool:
        """检查状态是否完整（工作流已完成）

        Args:
            state: 研究状态

        Returns:
            是否完成
        """
        return state.get("current_step") == "report_completed" and bool(state.get("report"))

    @staticmethod
    def get_state_progress(state: ResearchState) -> Dict[str, Any]:
        """获取状态进度

        Args:
            state: 研究状态

        Returns:
            进度信息字典
        """
        step_order = [
            "init", "planning_completed",
            "search_completed", "reading_completed",
            "analysis_completed", "report_completed"
        ]

        current_step = state.get("current_step", "init")

        # 计算进度百分比
        if current_step in step_order:
            progress = (step_order.index(current_step) / (len(step_order) - 1)) * 100
        elif "failed" in current_step:
            progress = -1  # 表示失败
        else:
            progress = 0

        return {
            "current_step": current_step,
            "progress_percent": round(progress, 1),
            "papers_found": len(state.get("papers", [])),
            "papers_processed": len(state.get("paper_summaries", [])),
            "has_report": bool(state.get("report")),
            "is_complete": StateValidator.is_state_complete(state),
        }


def get_state_summary(state: ResearchState) -> Dict[str, Any]:
    """获取状态摘要（便捷函数）

    Args:
        state: 研究状态

    Returns:
        状态摘要字典
    """
    start_time = state.get("start_time")
    end_time = state.get("end_time")

    duration = None
    if start_time and end_time and isinstance(start_time, datetime) and isinstance(end_time, datetime):
        duration = (end_time - start_time).total_seconds()

    return {
        "query": state.get("query", "N/A"),
        "current_step": state.get("current_step", "unknown"),
        "duration_seconds": duration,
        "papers_count": len(state.get("papers", [])),
        "summaries_count": len(state.get("paper_summaries", [])),
        "has_analysis": bool(state.get("analysis")),
        "has_report": bool(state.get("report")),
        "message_count": len(state.get("messages", [])),
        "error_count": len(state.get("errors", [])),
    }
