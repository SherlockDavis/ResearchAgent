"""Planner Agent 测试脚本"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.state import create_initial_state


class MockPlanner:
    """Mock Planner用于测试无需LLM的功能"""
    def __init__(self):
        self.name = "Planner"
        self.memory = []

    def add_to_memory(self, role: str, content: str) -> None:
        """添加消息到记忆"""
        self.memory.append({"role": role, "content": content})

    def clear_memory(self) -> None:
        """清空记忆"""
        self.memory.clear()

    def get_memory(self):
        """获取记忆"""
        return self.memory.copy()

    def get_task_by_id(self, state: dict, task_id: str):
        """根据ID获取子任务"""
        for task in state.get("sub_tasks", []):
            if task.get("id") == task_id:
                return task
        return None

    def get_ready_tasks(self, state: dict):
        """获取可以执行的子任务"""
        ready_tasks = []
        for task in state.get("sub_tasks", []):
            if task.get("status") == "pending":
                dependencies = task.get("dependencies", [])
                all_deps_completed = True
                for dep_id in dependencies:
                    dep_task = self.get_task_by_id(state, dep_id)
                    if not dep_task or dep_task.get("status") != "completed":
                        all_deps_completed = False
                        break
                if all_deps_completed:
                    ready_tasks.append(task)
        return ready_tasks

    def _parse_plan_response(self, content: str):
        """解析LLM返回的任务计划"""
        import json
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


def test_planner_basic():
    """测试Planner基本功能（无需LLM）"""
    print("=" * 60)
    print("测试1: Planner Agent基本功能测试")
    print("=" * 60)

    planner = MockPlanner()
    print(f"✓ PlannerAgent对象创建成功")

    # 测试记忆功能
    planner.add_to_memory("user", "测试消息")
    memory = planner.get_memory()
    assert len(memory) == 1
    print(f"✓ 记忆功能正常，当前记忆数: {len(memory)}")

    # 清空记忆
    planner.clear_memory()
    assert len(planner.get_memory()) == 0
    print("✓ 清空记忆功能正常")

    print("\n基本功能测试通过！\n")


def test_parse_plan_response():
    """测试计划响应解析功能"""
    print("=" * 60)
    print("测试2: 计划响应解析功能测试")
    print("=" * 60)

    planner = MockPlanner()

    # 测试用例1: 标准JSON
    test_case_1 = '''{
        "sub_tasks": [
            {"id": "task_1", "description": "搜索论文", "agent_type": "searcher", "dependencies": []}
        ],
        "plan_summary": "测试计划"
    }'''

    result = planner._parse_plan_response(test_case_1)
    assert "sub_tasks" in result
    assert len(result["sub_tasks"]) == 1
    print("✓ 标准JSON解析成功")

    # 测试用例2: Markdown代码块
    test_case_2 = '''```json
    {
        "sub_tasks": [
            {"id": "task_1", "description": "搜索论文", "agent_type": "searcher", "dependencies": []}
        ],
        "plan_summary": "测试计划"
    }
    ```'''

    result = planner._parse_plan_response(test_case_2)
    assert "sub_tasks" in result
    print("✓ Markdown代码块解析成功")

    # 测试用例3: 带额外文本的JSON
    test_case_3 = '''好的，这是任务计划：
    {
        "sub_tasks": [
            {"id": "task_1", "description": "搜索论文", "agent_type": "searcher", "dependencies": []}
        ],
        "plan_summary": "测试计划"
    }
    希望这个计划能满足您的需求。'''

    result = planner._parse_plan_response(test_case_3)
    assert "sub_tasks" in result
    print("✓ 带额外文本的JSON解析成功")

    print("\n解析功能测试通过！\n")


def test_task_management():
    """测试任务管理功能"""
    print("=" * 60)
    print("测试3: 任务管理功能测试")
    print("=" * 60)

    planner = MockPlanner()

    # 创建模拟状态
    state = {
        "sub_tasks": [
            {"id": "task_1", "description": "搜索", "agent_type": "searcher", "status": "completed", "dependencies": []},
            {"id": "task_2", "description": "阅读", "agent_type": "reader", "status": "pending", "dependencies": ["task_1"]},
            {"id": "task_3", "description": "分析", "agent_type": "analyst", "status": "pending", "dependencies": ["task_2"]},
            {"id": "task_4", "description": "搜索2", "agent_type": "searcher", "status": "pending", "dependencies": []},
        ]
    }

    # 测试get_task_by_id
    task = planner.get_task_by_id(state, "task_2")
    assert task is not None
    assert task["id"] == "task_2"
    print("✓ get_task_by_id功能正常")

    # 测试获取不存在的任务
    task = planner.get_task_by_id(state, "task_999")
    assert task is None
    print("✓ 获取不存在任务返回None")

    # 测试get_ready_tasks
    ready_tasks = planner.get_ready_tasks(state)
    # task_1已完成，task_2依赖task_1所以可执行，task_4无依赖所以可执行
    assert len(ready_tasks) == 2
    ready_ids = [t["id"] for t in ready_tasks]
    assert "task_2" in ready_ids
    assert "task_4" in ready_ids
    print(f"✓ get_ready_tasks功能正常，找到{len(ready_tasks)}个可执行任务")

    print("\n任务管理功能测试通过！\n")


async def test_planner_execute():
    """测试Planner执行任务拆解（需要LLM API密钥）"""
    print("=" * 60)
    print("测试4: Planner任务拆解功能测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        print("  请设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        return True

    from agents.planner import PlannerAgent

    # 创建Planner实例
    planner = PlannerAgent()

    # 创建初始状态
    query = "帮我调研LLM reasoning最新进展"
    state = create_initial_state(query)
    print(f"输入研究问题: {query}")
    print(f"初始状态: {state['current_step']}")

    try:
        # 执行Planner
        result_state = await planner.execute(state)

        print(f"\n✓ Planner执行成功")
        print(f"当前步骤: {result_state['current_step']}")
        print(f"生成子任务数: {len(result_state.get('sub_tasks', []))}")

        # 打印子任务
        print("\n子任务列表:")
        for i, task in enumerate(result_state.get('sub_tasks', []), 1):
            print(f"  {i}. [{task['id']}] {task['agent_type']}")
            print(f"     描述: {task['description'][:60]}...")
            print(f"     依赖: {task.get('dependencies', [])}")
            print(f"     状态: {task['status']}")

        # 打印消息日志
        print("\n执行日志:")
        for msg in result_state.get('messages', []):
            print(f"  [{msg['agent']}] {msg['message'][:80]}...")

        return True

    except Exception as e:
        print(f"\n✗ Planner执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_import():
    """测试模块导入"""
    print("=" * 60)
    print("测试0: 模块导入测试")
    print("=" * 60)

    try:
        from agents import PlannerAgent
        print("✓ 从agents导入PlannerAgent成功")
    except ImportError as e:
        print(f"✗ 从agents导入失败: {e}")
        return False

    try:
        from agents.planner import PlannerAgent
        print("✓ 从agents.planner导入PlannerAgent成功")
    except ImportError as e:
        print(f"✗ 从agents.planner导入失败: {e}")
        return False

    try:
        from prompts.planner import load_prompt
        print("✗ prompts.planner不应存在")
    except ImportError:
        print("✓ prompts.planner正确不存在（prompts是txt文件）")

    print("\n模块导入测试通过！\n")
    return True


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Planner Agent 测试套件")
    print("=" * 60 + "\n")

    # 运行所有测试
    success = True

    success = test_import() and success
    test_planner_basic()
    test_parse_plan_response()
    test_task_management()

    # 执行实际LLM调用测试（需要配置API密钥）
    success = await test_planner_execute() and success

    print("=" * 60)
    if success:
        print("所有测试通过！✓")
    else:
        print("部分测试失败 ✗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
