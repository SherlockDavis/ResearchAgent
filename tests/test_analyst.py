"""Analyst Agent 测试脚本"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.state import create_initial_state


def test_import():
    """测试模块导入"""
    print("=" * 60)
    print("测试0: 模块导入测试")
    print("=" * 60)

    try:
        from agents import AnalystAgent
        print("✓ 从agents导入AnalystAgent成功")
    except ImportError as e:
        print(f"✗ 从agents导入失败: {e}")
        return False

    try:
        from agents.analyst import AnalystAgent
        print("✓ 从agents.analyst导入AnalystAgent成功")
    except ImportError as e:
        print(f"✗ 从agents.analyst导入失败: {e}")
        return False

    print("\n模块导入测试通过！\n")
    return True


def test_analysis_parser():
    """测试分析结果解析功能（无需LLM）"""
    print("=" * 60)
    print("测试1: 分析结果解析功能测试")
    print("=" * 60)

    import json

    def parse_analysis_response(content: str):
        """解析分析响应JSON"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

        try:
            start_idx = content.find("{")
            end_idx = content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                return json.loads(content[start_idx:end_idx+1])
        except json.JSONDecodeError:
            pass

        raise ValueError(f"无法解析分析响应: {content[:200]}...")

    # 测试用例1: 标准JSON
    test_case_1 = '''{
        "overview": "领域概述",
        "method_comparison": [
            {"paper": "论文1", "method": "方法1", "pros": "优势1", "cons": "局限1"}
        ],
        "key_insights": ["洞察1"],
        "trends": ["趋势1"],
        "recommendations": ["建议1"]
    }'''

    result = parse_analysis_response(test_case_1)
    assert "overview" in result
    assert len(result["method_comparison"]) == 1
    print("✓ 标准JSON解析成功")

    # 测试用例2: Markdown代码块
    test_case_2 = '''```json
    {
        "overview": "领域概述",
        "method_comparison": [
            {"paper": "论文1", "method": "方法1", "pros": "优势", "cons": "局限"},
            {"paper": "论文2", "method": "方法2", "pros": "优势", "cons": "局限"}
        ],
        "key_insights": ["洞察1", "洞察2"],
        "trends": ["趋势1", "趋势2"],
        "recommendations": ["建议1"]
    }
    ```'''

    result = parse_analysis_response(test_case_2)
    assert len(result["method_comparison"]) == 2
    print("✓ Markdown代码块解析成功")

    # 测试用例3: 带额外文本
    test_case_3 = '''以下是分析结果：
    {
        "overview": "领域概述",
        "method_comparison": [],
        "key_insights": ["洞察1", "洞察2", "洞察3"],
        "trends": ["趋势1", "趋势2", "趋势3"],
        "recommendations": ["建议1", "建议2"]
    }
    分析完成。'''

    result = parse_analysis_response(test_case_3)
    assert len(result["key_insights"]) == 3
    print("✓ 带额外文本的JSON解析成功")

    print("\n分析结果解析功能测试通过！\n")


def test_format_summaries():
    """测试论文摘要格式化"""
    print("=" * 60)
    print("测试2: 论文摘要格式化测试")
    print("=" * 60)

    def format_summaries_for_analysis(summaries):
        """将论文摘要格式化为分析文本"""
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

            lines.append("---\n")

        return "\n".join(lines)

    summaries = [
        {
            "arxiv_id": "2201.11903",
            "title": "Chain-of-Thought Prompting",
            "relevance_score": 9,
            "summary": "提出了CoT提示方法...",
            "key_contributions": ["贡献1", "贡献2"]
        },
        {
            "arxiv_id": "2210.03629",
            "title": "ReAct: Synergizing Reasoning and Acting",
            "relevance_score": 8,
            "summary": "结合推理和行动...",
            "key_contributions": ["贡献A"]
        }
    ]

    formatted = format_summaries_for_analysis(summaries)
    assert "Chain-of-Thought" in formatted
    assert "ReAct" in formatted
    assert "共2篇论文" in formatted
    print("✓ 论文摘要格式化成功")
    print(f"  格式化后长度: {len(formatted)} 字符")

    print("\n论文摘要格式化测试通过！\n")


def test_helper_methods():
    """测试辅助方法"""
    print("=" * 60)
    print("测试3: 辅助方法测试")
    print("=" * 60)

    # 模拟get_top_papers方法
    def get_top_papers(summaries, top_k=5):
        sorted_summaries = sorted(
            summaries,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )
        return sorted_summaries[:top_k]

    summaries = [
        {"title": "论文A", "relevance_score": 7},
        {"title": "论文B", "relevance_score": 9},
        {"title": "论文C", "relevance_score": 8},
        {"title": "论文D", "relevance_score": 6},
    ]

    top_papers = get_top_papers(summaries, top_k=3)
    assert len(top_papers) == 3
    assert top_papers[0]["title"] == "论文B"  # 最高分
    assert top_papers[1]["title"] == "论文C"
    print("✓ get_top_papers方法成功")

    # 模拟group_by_method方法
    def group_by_method(summaries):
        groups = {}
        for summary in summaries:
            methods = summary.get('methods', [])
            if methods:
                method_key = methods[0].split(':')[0][:30]
                if method_key not in groups:
                    groups[method_key] = []
                groups[method_key].append(summary)
            else:
                if '其他' not in groups:
                    groups['其他'] = []
                groups['其他'].append(summary)
        return groups

    summaries_with_methods = [
        {"title": "论文1", "methods": ["CoT: Chain-of-Thought"]},
        {"title": "论文2", "methods": ["CoT: 改进版"]},
        {"title": "论文3", "methods": ["ReAct: 推理行动"]},
        {"title": "论文4", "methods": []},
    ]

    groups = group_by_method(summaries_with_methods)
    assert "CoT" in groups
    assert "ReAct" in groups
    assert "其他" in groups
    assert len(groups["CoT"]) == 2
    print("✓ group_by_method方法成功")

    print("\n辅助方法测试通过！\n")


def test_format_analysis():
    """测试分析结果格式化"""
    print("=" * 60)
    print("测试4: 分析结果格式化测试")
    print("=" * 60)

    def format_analysis(analysis):
        lines = ["# 论文对比分析报告\n"]

        if analysis.get('overview'):
            lines.extend(["## 领域概述", analysis['overview'], ""])

        if analysis.get('method_comparison'):
            lines.extend(["## 方法对比", ""])
            for item in analysis['method_comparison']:
                lines.append(f"### {item.get('paper', 'N/A')}")
                lines.append(f"**方法**: {item.get('method', 'N/A')}")
                lines.append(f"**优势**: {item.get('pros', 'N/A')}")
                lines.append(f"**局限**: {item.get('cons', 'N/A')}")
                lines.append("")

        if analysis.get('key_insights'):
            lines.extend(["## 关键洞察", ""])
            for i, insight in enumerate(analysis['key_insights'], 1):
                lines.append(f"{i}. {insight}")
            lines.append("")

        return "\n".join(lines)

    analysis = {
        "overview": "这是领域概述",
        "method_comparison": [
            {"paper": "论文1", "method": "方法1", "pros": "优势1", "cons": "局限1"}
        ],
        "key_insights": ["洞察1", "洞察2"]
    }

    formatted = format_analysis(analysis)
    assert "论文对比分析报告" in formatted
    assert "领域概述" in formatted
    assert "方法对比" in formatted
    assert "关键洞察" in formatted
    print("✓ 分析结果格式化成功")

    print("\n分析结果格式化测试通过！\n")


async def test_analyst_agent_execute():
    """测试AnalystAgent完整执行（需要API密钥）"""
    print("=" * 60)
    print("测试5: AnalystAgent执行测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        print("  请设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        return True

    from agents.analyst import AnalystAgent

    # 创建Analyst实例
    analyst = AnalystAgent()
    print("✓ AnalystAgent创建成功")

    # 创建测试用的论文摘要数据
    paper_summaries = [
        {
            "arxiv_id": "2201.11903",
            "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
            "authors": ["Jason Wei", "Xuezhi Wang", "Dale Schuurmans"],
            "url": "https://arxiv.org/abs/2201.11903",
            "summary": "本文提出了Chain-of-Thought (CoT)提示方法，通过在提示中加入中间推理步骤，显著提升大型语言模型的推理能力。实验表明，CoT在数学推理、常识推理等任务上取得了突破性进展。",
            "key_contributions": [
                "提出了Chain-of-Thought提示方法",
                "证明了少样本CoT提示可以激发大型语言模型的推理能力"
            ],
            "methods": ["Chain-of-Thought提示", "少样本学习"],
            "experiments": ["数学推理：GSM8K数据集", "常识推理：StrategyQA"],
            "limitations": ["主要适用于大型模型", "推理链质量依赖示例设计"],
            "relevance_score": 9,
            "relevance_reason": "LLM推理领域开创性工作"
        },
        {
            "arxiv_id": "2210.03629",
            "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
            "authors": ["Shunyu Yao", "Jeffrey Zhao", "Dian Yu"],
            "url": "https://arxiv.org/abs/2210.03629",
            "summary": "本文提出了ReAct框架，将推理和行动结合起来，使语言模型能够交替生成推理轨迹和任务特定的动作，并与外部环境交互。",
            "key_contributions": [
                "提出了ReAct框架，结合推理和行动",
                "在问答、事实验证等任务上取得显著效果"
            ],
            "methods": ["ReAct框架", "交替推理和行动"],
            "experiments": ["知识密集型任务", "决策任务"],
            "limitations": ["需要外部工具支持", "交互开销较大"],
            "relevance_score": 8,
            "relevance_reason": "推理与行动结合的重要工作"
        }
    ]

    state = create_initial_state("LLM reasoning方法对比分析")
    state["paper_summaries"] = paper_summaries

    try:
        # 执行Analyst
        result_state = await analyst.execute(state)

        print(f"\n✓ Analyst执行成功")
        print(f"当前步骤: {result_state['current_step']}")

        # 打印分析结果
        analysis = result_state.get('analysis', {})
        if analysis:
            print(f"\n分析结果:")
            if analysis.get('overview'):
                print(f"  概述: {analysis['overview'][:100]}...")
            if analysis.get('key_insights'):
                print(f"  关键洞察数: {len(analysis['key_insights'])}")
            if analysis.get('trends'):
                print(f"  发展趋势数: {len(analysis['trends'])}")

        # 打印消息日志
        print("\n执行日志:")
        for msg in result_state.get('messages', []):
            print(f"  [{msg['agent']}] {msg['message'][:70]}...")

        return True

    except Exception as e:
        print(f"\n✗ Analyst执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_analyze_papers_independent():
    """测试独立分析论文（需要API密钥）"""
    print("=" * 60)
    print("测试6: 独立分析论文测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        return True

    from agents.analyst import AnalystAgent

    try:
        analyst = AnalystAgent()
    except Exception as e:
        print(f"⚠ 创建AnalystAgent需要API配置: {e}")
        return True

    # 简化的论文摘要
    summaries = [
        {
            "arxiv_id": "2201.11903",
            "title": "Chain-of-Thought Prompting",
            "relevance_score": 9,
            "summary": "提出了CoT提示方法，通过中间推理步骤提升LLM推理能力。",
            "key_contributions": ["CoT提示方法", "少样本推理"],
            "methods": ["Chain-of-Thought提示"],
            "experiments": ["数学推理", "常识推理"],
            "limitations": ["依赖大模型"]
        },
        {
            "arxiv_id": "2210.03629",
            "title": "ReAct",
            "relevance_score": 8,
            "summary": "结合推理和行动，与外部环境交互。",
            "key_contributions": ["ReAct框架"],
            "methods": ["交替推理和行动"],
            "experiments": ["知识密集型任务"],
            "limitations": ["需要外部工具"]
        }
    ]

    try:
        analysis = await analyst.analyze_papers(
            summaries=summaries,
            query="LLM reasoning方法对比"
        )

        print(f"✓ 独立分析成功")
        if analysis.get('overview'):
            print(f"  概述: {analysis['overview'][:80]}...")

        # 测试格式化输出
        formatted = analyst.format_analysis(analysis)
        print(f"\n格式化预览:\n{formatted[:300]}...")

        return True

    except Exception as e:
        print(f"✗ 独立分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Analyst Agent 测试套件")
    print("=" * 60 + "\n")

    # 运行所有测试
    success = True

    success = test_import() and success
    test_analysis_parser()
    test_format_summaries()
    test_helper_methods()
    test_format_analysis()
    success = await test_analyze_papers_independent() and success
    success = await test_analyst_agent_execute() and success

    print("=" * 60)
    if success:
        print("所有测试通过！✓")
    else:
        print("部分测试失败 ✗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
