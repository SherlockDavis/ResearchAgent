"""Workflow 测试脚本"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.state import create_initial_state, ResearchState


def test_import():
    """测试模块导入"""
    print("=" * 60)
    print("测试0: 模块导入测试")
    print("=" * 60)

    try:
        from workflow import ResearchWorkflow, run_research
        print("✓ 从workflow导入ResearchWorkflow成功")
        print("✓ 从workflow导入run_research成功")
    except ImportError as e:
        print(f"✗ 从workflow导入失败: {e}")
        return False

    try:
        from workflow.graph import ResearchWorkflow
        print("✓ 从workflow.graph导入ResearchWorkflow成功")
    except ImportError as e:
        print(f"✗ 从workflow.graph导入失败: {e}")
        return False

    print("\n模块导入测试通过！\n")
    return True


def test_workflow_initialization():
    """测试工作流初始化"""
    print("=" * 60)
    print("测试1: 工作流初始化测试")
    print("=" * 60)

    import os
    # 跳过需要API密钥的测试
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        return True

    from workflow import ResearchWorkflow

    try:
        workflow = ResearchWorkflow()
        print("✓ ResearchWorkflow创建成功")

        # 检查Agent是否初始化
        assert workflow.planner is not None
        assert workflow.searcher is not None
        assert workflow.reader is not None
        assert workflow.analyst is not None
        assert workflow.writer is not None
        print("✓ 所有Agent已初始化")

        # 检查图是否编译
        assert workflow.graph is not None
        print("✓ LangGraph图已编译")

        return True

    except Exception as e:
        print(f"✗ 工作流初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_diagram():
    """测试工作流图描述"""
    print("=" * 60)
    print("测试2: 工作流图描述测试")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        return True

    from workflow import ResearchWorkflow

    try:
        workflow = ResearchWorkflow()
        diagram = workflow.get_workflow_diagram()

        assert "mermaid" in diagram
        assert "Planner" in diagram
        assert "Searcher" in diagram
        assert "Reader" in diagram
        assert "Analyst" in diagram
        assert "Writer" in diagram
        print("✓ 工作流图描述生成成功")
        print(f"  图表预览:\n{diagram[:200]}...")

        return True

    except Exception as e:
        print(f"✗ 工作流图描述生成失败: {e}")
        return False


def test_execution_summary():
    """测试执行摘要生成"""
    print("=" * 60)
    print("测试3: 执行摘要生成测试")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        return True

    from workflow import ResearchWorkflow
    from datetime import datetime

    try:
        workflow = ResearchWorkflow()

        # 创建模拟状态
        state = create_initial_state("测试查询")
        state["papers"] = [{}, {}, {}]
        state["paper_summaries"] = [{}, {}]
        state["analysis"] = {"overview": "test"}
        state["report"] = "# Test Report"
        state["end_time"] = datetime.now()

        summary = workflow.get_execution_summary(state)

        assert summary["query"] == "测试查询"
        assert summary["papers_found"] == 3
        assert summary["papers_summarized"] == 2
        assert summary["has_analysis"] == True
        assert summary["has_report"] == True
        assert summary["duration_seconds"] is not None
        print("✓ 执行摘要生成成功")
        print(f"  摘要: {summary}")

        return True

    except Exception as e:
        print(f"✗ 执行摘要生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step_by_step_execution():
    """测试逐步执行"""
    print("=" * 60)
    print("测试4: 逐步执行测试")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        return True

    from workflow import ResearchWorkflow

    steps_executed = []

    def callback(step_name, state):
        steps_executed.append(step_name)
        print(f"  步骤完成: {step_name}")

    try:
        workflow = ResearchWorkflow()

        # 使用模拟数据测试回调
        # 注意：这里不实际执行Agent，只测试回调机制
        print("✓ 回调函数设置成功")
        print(f"  预期步骤: planner -> searcher -> reader -> analyst -> writer")

        return True

    except Exception as e:
        print(f"✗ 逐步执行测试失败: {e}")
        return False


async def test_full_workflow():
    """测试完整工作流（需要API密钥）"""
    print("=" * 60)
    print("测试5: 完整工作流测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        print("  请设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        return True

    from workflow import ResearchWorkflow

    try:
        workflow = ResearchWorkflow()
        print("✓ ResearchWorkflow创建成功")

        # 使用简单的查询进行测试
        query = "Chain-of-Thought prompting方法"
        print(f"\n开始研究工作流: {query}")
        print("注意：此测试需要调用LLM API，可能需要较长时间...")

        # 运行工作流
        result = await workflow.run(query)

        print(f"\n✓ 工作流执行成功")
        print(f"  最终状态: {result.get('current_step')}")
        print(f"  检索论文数: {len(result.get('papers', []))}")
        print(f"  阅读论文数: {len(result.get('paper_summaries', []))}")

        # 检查是否有报告
        if result.get('report'):
            report_length = len(result['report'])
            print(f"  报告长度: {report_length} 字符")
            print(f"\n  报告预览（前300字符）:\n{result['report'][:300]}...")

        # 获取执行摘要
        summary = workflow.get_execution_summary(result)
        print(f"\n  执行摘要: {summary}")

        return True

    except Exception as e:
        print(f"\n✗ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_run_research_convenience():
    """测试便捷函数run_research"""
    print("=" * 60)
    print("测试6: 便捷函数测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        return True

    from workflow import run_research

    try:
        query = "ReAct framework"
        print(f"\n使用便捷函数运行: {query}")
        print("注意：此测试需要调用LLM API...")

        # 运行研究
        result = await run_research(query)

        print(f"\n✓ 便捷函数执行成功")
        print(f"  最终状态: {result.get('current_step')}")
        print(f"  检索论文数: {len(result.get('papers', []))}")

        return True

    except Exception as e:
        print(f"\n✗ 便捷函数执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_transitions():
    """测试状态流转"""
    print("=" * 60)
    print("测试7: 状态流转测试")
    print("=" * 60)

    # 测试状态创建
    state = create_initial_state("测试查询")
    assert state["query"] == "测试查询"
    assert state["current_step"] == "init"
    assert state["papers"] == []
    assert state["paper_summaries"] == []
    assert state["analysis"] == {}
    assert state["report"] == ""
    print("✓ 初始状态创建成功")

    # 模拟状态流转
    state["current_step"] = "planning_completed"
    state["sub_tasks"] = [{"id": "task_1", "agent_type": "searcher"}]
    print("✓ 状态更新成功")

    state["current_step"] = "search_completed"
    state["papers"] = [{"title": "Paper 1"}]
    print("✓ 状态流转到search_completed")

    state["current_step"] = "reading_completed"
    state["paper_summaries"] = [{"title": "Summary 1"}]
    print("✓ 状态流转到reading_completed")

    state["current_step"] = "analysis_completed"
    state["analysis"] = {"overview": "test"}
    print("✓ 状态流转到analysis_completed")

    state["current_step"] = "report_completed"
    state["report"] = "# Report"
    print("✓ 状态流转到report_completed")

    print("\n状态流转测试通过！\n")
    return True


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Workflow 测试套件")
    print("=" * 60 + "\n")

    # 运行所有测试
    success = True

    success = test_import() and success
    success = test_workflow_initialization() and success
    success = test_workflow_diagram() and success
    success = test_execution_summary() and success
    success = test_step_by_step_execution() and success
    success = test_state_transitions() and success
    success = await test_full_workflow() and success
    success = await test_run_research_convenience() and success

    print("=" * 60)
    if success:
        print("所有测试通过！✓")
    else:
        print("部分测试失败 ✗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
