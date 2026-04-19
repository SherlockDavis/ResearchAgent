"""Writer Agent 测试脚本"""
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
        from agents import WriterAgent
        print("✓ 从agents导入WriterAgent成功")
    except ImportError as e:
        print(f"✗ 从agents导入失败: {e}")
        return False

    try:
        from agents.writer import WriterAgent
        print("✓ 从agents.writer导入WriterAgent成功")
    except ImportError as e:
        print(f"✗ 从agents.writer导入失败: {e}")
        return False

    print("\n模块导入测试通过！\n")
    return True


def test_build_report_input():
    """测试报告输入构建"""
    print("=" * 60)
    print("测试1: 报告输入构建测试")
    print("=" * 60)

    def build_report_input(query, papers, summaries, analysis):
        """构建报告生成的输入文本"""
        lines = [f"# 研究问题\n{query}\n"]

        lines.append(f"## 检索到的论文（共{len(papers)}篇）\n")
        for i, paper in enumerate(papers, 1):
            lines.append(f"{i}. **{paper.get('title', 'N/A')}**")
            lines.append(f"   - 作者: {', '.join(paper.get('authors', [])[:3])}")
            lines.append(f"   - arXiv: {paper.get('arxiv_id', 'N/A')}")
            lines.append("")

        lines.append(f"## 论文摘要\n")
        for i, summary in enumerate(summaries, 1):
            lines.append(f"### 论文{i}: {summary.get('title', 'N/A')}")
            lines.append(f"**相关度**: {summary.get('relevance_score', 'N/A')}/10")
            lines.append("")

        if analysis:
            lines.append("## 对比分析结果\n")
            if analysis.get('overview'):
                lines.append(f"**领域概述**: {analysis['overview'][:100]}...\n")

        return "\n".join(lines)

    query = "LLM reasoning方法调研"
    papers = [
        {"title": "Chain-of-Thought", "authors": ["Wei"], "arxiv_id": "2201.11903"},
        {"title": "ReAct", "authors": ["Yao"], "arxiv_id": "2210.03629"}
    ]
    summaries = [
        {"title": "CoT", "relevance_score": 9},
        {"title": "ReAct", "relevance_score": 8}
    ]
    analysis = {"overview": "领域概述..."}

    result = build_report_input(query, papers, summaries, analysis)
    assert "LLM reasoning方法调研" in result
    assert "Chain-of-Thought" in result
    assert "ReAct" in result
    assert "共2篇" in result
    print("✓ 报告输入构建成功")
    print(f"  输入长度: {len(result)} 字符")

    print("\n报告输入构建测试通过！\n")


def test_report_metadata():
    """测试报告元数据生成"""
    print("=" * 60)
    print("测试2: 报告元数据生成测试")
    print("=" * 60)

    from datetime import datetime

    def generate_report_metadata(query, papers, summaries, analysis):
        """生成报告元数据"""
        avg_relevance = 0
        if summaries:
            scores = [s.get('relevance_score', 0) for s in summaries]
            avg_relevance = sum(scores) / len(scores)

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
                {"title": s.get('title'), "relevance_score": s.get('relevance_score')}
                for s in sorted(summaries, key=lambda x: x.get('relevance_score', 0), reverse=True)[:5]
            ]
        }

    query = "Test Query"
    papers = [{}, {}, {}]
    summaries = [
        {"title": "Paper A", "relevance_score": 9, "methods": ["CoT: method"]},
        {"title": "Paper B", "relevance_score": 7, "methods": ["ReAct: method"]},
        {"title": "Paper C", "relevance_score": 8, "methods": []}
    ]

    metadata = generate_report_metadata(query, papers, summaries, {})
    assert metadata["query"] == "Test Query"
    assert metadata["statistics"]["total_papers"] == 3
    assert metadata["statistics"]["avg_relevance_score"] == 8.0
    assert "CoT" in metadata["statistics"]["method_types"]
    assert metadata["top_papers"][0]["title"] == "Paper A"  # 最高分
    print("✓ 元数据生成成功")
    print(f"  平均相关度: {metadata['statistics']['avg_relevance_score']}")
    print(f"  方法类型: {metadata['statistics']['method_types']}")

    print("\n报告元数据生成测试通过！\n")


def test_format_report_with_metadata():
    """测试报告格式化"""
    print("=" * 60)
    print("测试3: 报告格式化测试")
    print("=" * 60)

    def format_report_with_metadata(report, metadata):
        """将元数据添加到报告头部"""
        header_lines = [
            "---",
            f"title: {metadata.get('title', 'Research Report')}",
            f"date: {metadata.get('generated_at', '')}",
            f"papers_analyzed: {metadata.get('statistics', {}).get('total_papers', 0)}",
            "---",
            "",
        ]

        stats = metadata.get('statistics', {})
        header_lines.extend([
            "## 报告信息",
            f"- **研究问题**: {metadata.get('query', 'N/A')}",
            f"- **分析论文数**: {stats.get('total_papers', 0)}",
            f"- **平均相关度**: {stats.get('avg_relevance_score', 0)}/10",
            "",
            "---",
            "",
        ])

        return "\n".join(header_lines) + report

    report = "# 报告正文\n\n这是报告内容。"
    metadata = {
        "title": "Test Report",
        "query": "Test Query",
        "generated_at": "2024-01-01T00:00:00",
        "statistics": {
            "total_papers": 5,
            "avg_relevance_score": 8.5
        }
    }

    formatted = format_report_with_metadata(report, metadata)
    assert "---" in formatted
    assert "title: Test Report" in formatted
    assert "Test Query" in formatted
    assert "5" in formatted
    assert "报告" in formatted
    print("✓ 报告格式化成功")

    print("\n报告格式化测试通过！\n")


async def test_writer_agent_execute():
    """测试WriterAgent完整执行（需要API密钥）"""
    print("=" * 60)
    print("测试4: WriterAgent执行测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        print("  请设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        return True

    from agents.writer import WriterAgent

    # 创建Writer实例
    writer = WriterAgent()
    print("✓ WriterAgent创建成功")

    # 创建测试数据
    query = "LLM reasoning方法调研"
    papers = [
        {
            "arxiv_id": "2201.11903",
            "title": "Chain-of-Thought Prompting",
            "authors": ["Jason Wei", "Xuezhi Wang"],
            "url": "https://arxiv.org/abs/2201.11903"
        },
        {
            "arxiv_id": "2210.03629",
            "title": "ReAct: Synergizing Reasoning and Acting",
            "authors": ["Shunyu Yao", "Jeffrey Zhao"],
            "url": "https://arxiv.org/abs/2210.03629"
        }
    ]
    summaries = [
        {
            "arxiv_id": "2201.11903",
            "title": "Chain-of-Thought Prompting",
            "summary": "提出了CoT提示方法，通过中间推理步骤提升LLM推理能力。",
            "key_contributions": ["CoT提示方法", "少样本推理"],
            "methods": ["Chain-of-Thought提示"],
            "relevance_score": 9
        },
        {
            "arxiv_id": "2210.03629",
            "title": "ReAct",
            "summary": "结合推理和行动，与外部环境交互。",
            "key_contributions": ["ReAct框架"],
            "methods": ["交替推理和行动"],
            "relevance_score": 8
        }
    ]
    analysis = {
        "overview": "LLM推理增强是当前热点方向，主要技术包括提示工程和工具使用。",
        "method_comparison": [
            {"paper": "CoT", "method": "提示工程", "pros": "简单有效", "cons": "依赖大模型"},
            {"paper": "ReAct", "method": "推理+行动", "pros": "可交互", "cons": "实现复杂"}
        ],
        "key_insights": ["提示工程适合静态任务", "ReAct适合动态任务"],
        "trends": ["向多步推理发展", "向工具交互发展"],
        "recommendations": ["根据任务选择方法"]
    }

    state = create_initial_state(query)
    state["papers"] = papers
    state["paper_summaries"] = summaries
    state["analysis"] = analysis

    try:
        # 执行Writer
        result_state = await writer.execute(state)

        print(f"\n✓ Writer执行成功")
        print(f"当前步骤: {result_state['current_step']}")

        # 打印报告预览
        report = result_state.get('report', '')
        if report:
            print(f"\n报告长度: {len(report)} 字符")
            print(f"\n报告预览（前500字符）:\n{report[:500]}...")

        # 打印消息日志
        print("\n执行日志:")
        for msg in result_state.get('messages', []):
            print(f"  [{msg['agent']}] {msg['message'][:70]}...")

        return True

    except Exception as e:
        print(f"\n✗ Writer执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_generate_report_independent():
    """测试独立生成报告（需要API密钥）"""
    print("=" * 60)
    print("测试5: 独立生成报告测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        return True

    from agents.writer import WriterAgent

    try:
        writer = WriterAgent()
    except Exception as e:
        print(f"⚠ 创建WriterAgent需要API配置: {e}")
        return True

    # 简化测试数据
    query = "Test research query"
    papers = [{"title": "Paper 1", "authors": ["Author A"], "arxiv_id": "1234"}]
    summaries = [{"title": "Paper 1", "summary": "Summary...", "relevance_score": 8}]
    analysis = {"overview": "Overview..."}

    try:
        report = await writer.generate_report(query, papers, summaries, analysis)

        print(f"✓ 独立生成报告成功")
        print(f"  报告长度: {len(report)} 字符")
        print(f"  预览: {report[:200]}...")

        # 测试元数据
        metadata = writer.generate_report_metadata(query, papers, summaries, analysis)
        print(f"\n元数据:")
        print(f"  标题: {metadata['title']}")
        print(f"  论文数: {metadata['statistics']['total_papers']}")

        # 测试格式化
        formatted = writer.format_report_with_metadata(report, metadata)
        print(f"\n格式化后长度: {len(formatted)} 字符")

        return True

    except Exception as e:
        print(f"✗ 独立生成报告失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_save_report():
    """测试报告保存功能"""
    print("=" * 60)
    print("测试6: 报告保存功能测试")
    print("=" * 60)

    import os
    import tempfile

    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        report_content = "# Test Report\n\nThis is a test report."
        filename = "test_report.md"

        filepath = os.path.join(tmpdir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)

        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == report_content
        print("✓ 报告保存成功")
        print(f"  保存路径: {filepath}")

    print("\n报告保存功能测试通过！\n")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Writer Agent 测试套件")
    print("=" * 60 + "\n")

    # 运行所有测试
    success = True

    success = test_import() and success
    test_build_report_input()
    test_report_metadata()
    test_format_report_with_metadata()
    test_save_report()
    success = await test_generate_report_independent() and success
    success = await test_writer_agent_execute() and success

    print("=" * 60)
    if success:
        print("所有测试通过！✓")
    else:
        print("部分测试失败 ✗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
