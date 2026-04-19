"""Agent基类定义"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from langchain_core.language_models import BaseChatModel
from config import get_settings


class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, name: str, llm: Optional[BaseChatModel] = None):
        self.name = name
        self.settings = get_settings()
        self.llm = llm
        self.memory: List[Dict[str, Any]] = []

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行Agent任务

        Args:
            state: 当前状态字典，包含上下文信息

        Returns:
            更新后的状态字典
        """
        pass

    def add_to_memory(self, role: str, content: str) -> None:
        """添加消息到记忆"""
        self.memory.append({"role": role, "content": content})

    def clear_memory(self) -> None:
        """清空记忆"""
        self.memory.clear()

    def get_memory(self) -> List[Dict[str, Any]]:
        """获取记忆"""
        return self.memory.copy()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
