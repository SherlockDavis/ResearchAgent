"""Planner Agent - 任务拆解与分配"""
import json
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base import BaseAgent
from utils.llm import create_llm
from utils.state import SubTask, add_message
from utils.logger import logger


class PlannerAgent(BaseAgent):
    """Planner Agent负责将研究问题拆解为子任务并分配给其他Agent

    职责：
    1. 分析用户研究问题
    2. 拆解为可执行的子任务（搜索、阅读、分析等）
    3. 确定任务执行顺序和依赖关系
    4. 为每个子任务指定负责Agent
    """

    def __init__(self, llm=None):
        super().__init__(name="Planner", llm=llm)
        if self.llm is None:
            self.llm = create_llm()
        self._load_prompt()

    def _load_prompt(self) -> None:
        """加载Planner的系统Prompt"""
        try:
            with open("prompts/planner.txt", "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            # 使用默认prompt
            self.system_prompt = self._get_default_prompt()
            logger.warning("planner.txt not found, using default prompt")

    def _get_default_prompt(self) -> str:
        """获取默认的系统Prompt"""
        return """你是一个专业的科研任务规划专家。你的职责是将用户的研究问题拆解为结构化的子任务。

## 任务拆解原则
1. 分析用户的研究问题，理解其核心需求
2. 将问题拆解为3-5个可执行的子任务
3. 每个子任务应明确指定负责的Agent类型
4. 考虑任务之间的依赖关系

## Agent类型说明
- searcher: 负责检索相关论文，使用arXiv API搜索
- reader: 负责阅读论文，提取核心贡献、方法、实验结果
- analyst: 负责横向对比多篇论文，分析异同和优劣

## 输出格式
你必须以JSON格式输出，格式如下：
{
    "sub_tasks": [
        {
            "id": "task_1",
            "description": "任务描述",
            "agent_type": "searcher/reader/analyst",
            "dependencies": []
        }
    ],
    "plan_summary": "整体规划思路简述"
}

## 示例
用户问题："帮我调研LLM reasoning最新进展"

输出：
{
    "sub_tasks": [
        {
            "id": "task_1",
            "description": "检索LLM reasoning相关论文，重点关注Chain-of-Thought、Tree-of-Thought等方法的最新研究",
            "agent_type": "searcher",
            "dependencies": []
        },
        {
            "id": "task_2",
            "description": "阅读并总结检索到的论文，提取每篇论文的核心贡献、方法和实验结果",
            "agent_type": "reader",
            "dependencies": ["task_1"]
        },
        {
            "id": "task_3",
            "description": "对比分析不同reasoning方法的优劣、适用场景和性能表现",
            "agent_type": "analyst",
            "dependencies": ["task_2"]
        }
    ],
    "plan_summary": "首先检索LLM reasoning领域的最新论文，然后深入阅读提取关键信息，最后进行对比分析找出各方法的特点和差异。"
}

请确保输出是有效的JSON格式，不要包含任何其他解释文字。"""

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行Planner任务

        Args:
            state: 当前状态，包含用户query

        Returns:
            更新后的状态，包含sub_tasks
        """
        query = state.get("query", "")
        if not query:
            raise ValueError("Query is required in state")

        logger.info(f"Planner开始分析研究问题: {query[:100]}...")
        add_message(state, "Planner", f"开始分析研究问题: {query}")

        # 构建消息
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请为以下研究问题制定任务计划：\n\n{query}")
        ]

        try:
            # 调用LLM生成任务计划
            response = await self.llm.ainvoke(messages)
            content = response.content

            # 解析JSON响应
            plan_data = self._parse_plan_response(content)

            # 转换为SubTask对象列表
            sub_tasks = []
            for task_data in plan_data.get("sub_tasks", []):
                sub_task = SubTask(
                    id=task_data["id"],
                    description=task_data["description"],
                    agent_type=task_data["agent_type"],
                    dependencies=task_data.get("dependencies", [])
                )
                sub_tasks.append(sub_task)

            # 更新状态
            state["sub_tasks"] = [task.to_dict() for task in sub_tasks]
            state["current_step"] = "planning_completed"

            # 添加日志
            add_message(state, "Planner", f"任务计划已生成，共{len(sub_tasks)}个子任务")
            add_message(state, "Planner", f"规划摘要: {plan_data.get('plan_summary', '')}")

            # 记录到记忆
            self.add_to_memory("system", self.system_prompt)
            self.add_to_memory("user", query)
            self.add_to_memory("assistant", content)

            logger.info(f"Planner完成任务拆解，生成{len(sub_tasks)}个子任务")

            return state

        except Exception as e:
            error_msg = f"Planner执行失败: {str(e)}"
            logger.error(error_msg)
            add_message(state, "Planner", error_msg)
            state["current_step"] = "planning_failed"
            raise

    def _parse_plan_response(self, content: str) -> Dict[str, Any]:
        """解析LLM返回的任务计划

        Args:
            content: LLM响应内容

        Returns:
            解析后的计划数据
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

        raise ValueError(f"无法解析Planner响应: {content[:200]}...")

    def get_task_by_id(self, state: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """根据ID获取子任务

        Args:
            state: 当前状态
            task_id: 任务ID

        Returns:
            子任务字典，未找到返回None
        """
        for task in state.get("sub_tasks", []):
            if task.get("id") == task_id:
                return task
        return None

    def get_ready_tasks(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取可以执行的子任务（依赖已完成的）

        Args:
            state: 当前状态

        Returns:
            可执行的子任务列表
        """
        ready_tasks = []
        for task in state.get("sub_tasks", []):
            if task.get("status") == "pending":
                dependencies = task.get("dependencies", [])
                # 检查所有依赖是否已完成
                all_deps_completed = True
                for dep_id in dependencies:
                    dep_task = self.get_task_by_id(state, dep_id)
                    if not dep_task or dep_task.get("status") != "completed":
                        all_deps_completed = False
                        break

                if all_deps_completed:
                    ready_tasks.append(task)

        return ready_tasks
