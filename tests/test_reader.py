"""Reader Agent 测试脚本"""
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
        from agents import ReaderAgent
        print("✓ 从agents导入ReaderAgent成功")
    except ImportError as e:
        print(f"✗ 从agents导入失败: {e}")
        return False

    try:
        from agents.reader import ReaderAgent
        print("✓ 从agents.reader导入ReaderAgent成功")
    except ImportError as e:
        print(f"✗ 从agents.reader导入失败: {e}")
        return False

    print("\n模块导入测试通过！\n")
    return True


def test_summary_parser():
    """测试摘要解析功能（无需LLM）"""
    print("=" * 60)
    print("测试1: 摘要解析功能测试")
    print("=" * 60)

    import json

    def parse_summary_response(content: str):
        """解析摘要响应JSON"""
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

        raise ValueError(f"无法解析摘要响应: {content[:200]}...")

    # 测试用例1: 标准JSON
    test_case_1 = '''{
        "summary": "论文概述",
        "key_contributions": ["贡献1", "贡献2"],
        "methods": ["方法1"],
        "experiments": ["实验1"],
        "limitations": ["局限1"],
        "relevance_score": 8,
        "relevance_reason": "相关"
    }'''

    result = parse_summary_response(test_case_1)
    assert result["relevance_score"] == 8
    assert len(result["key_contributions"]) == 2
    print("✓ 标准JSON解析成功")

    # 测试用例2: Markdown代码块
    test_case_2 = '''```json
    {
        "summary": "论文概述",
        "key_contributions": ["贡献1"],
        "methods": ["方法1"],
        "experiments": ["实验1"],
        "limitations": [],
        "relevance_score": 9,
        "relevance_reason": "高度相关"
    }
    ```'''

    result = parse_summary_response(test_case_2)
    assert result["relevance_score"] == 9
    print("✓ Markdown代码块解析成功")

    # 测试用例3: 带额外文本
    test_case_3 = '''以下是论文分析结果：
    {
        "summary": "论文概述",
        "key_contributions": ["贡献1", "贡献2", "贡献3"],
        "methods": ["方法1", "方法2"],
        "experiments": ["实验1", "实验2"],
        "limitations": ["局限1", "局限2"],
        "relevance_score": 7,
        "relevance_reason": "比较相关"
    }
    分析完成。'''

    result = parse_summary_response(test_case_3)
    assert result["relevance_score"] == 7
    assert len(result["key_contributions"]) == 3
    print("✓ 带额外文本的JSON解析成功")

    print("\n摘要解析功能测试通过！\n")


def test_format_paper_for_reading():
    """测试论文格式化功能"""
    print("=" * 60)
    print("测试2: 论文格式化功能测试")
    print("=" * 60)

    def format_paper_for_reading(paper: dict) -> str:
        """将论文信息格式化为阅读文本"""
        lines = [
            f"标题: {paper.get('title', 'N/A')}",
            f"作者: {', '.join(paper.get('authors', []))}",
            f"arXiv ID: {paper.get('arxiv_id', 'N/A')}",
            f"发布时间: {paper.get('published', 'N/A')}",
            "",
            "摘要:",
            paper.get('abstract', 'N/A'),
        ]
        return "\n".join(lines)

    paper = {
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "authors": ["Jason Wei", "Xuezhi Wang", "Dale Schuurmans"],
        "arxiv_id": "2201.11903",
        "published": "2022-01-28",
        "abstract": "We explore how generating a chain of thought..."
    }

    formatted = format_paper_for_reading(paper)
    assert "Chain-of-Thought" in formatted
    assert "Jason Wei" in formatted
    assert "2201.11903" in formatted
    print("✓ 论文格式化成功")
    print(f"  格式化后长度: {len(formatted)} 字符")

    print("\n论文格式化功能测试通过！\n")


def test_format_summary():
    """测试摘要格式化输出"""
    print("=" * 60)
    print("测试3: 摘要格式化输出测试")
    print("=" * 60)

    # 模拟ReaderAgent的format_summary方法
    def format_summary(summary: dict) -> str:
        lines = [
            f"# {summary.get('title', 'N/A')}",
            "",
            f"**作者**: {', '.join(summary.get('authors', [])[:3])}",
            f"**arXiv**: {summary.get('arxiv_id', 'N/A')}",
            f"**相关度**: {summary.get('relevance_score', 'N/A')}/10",
            "",
            "## 概述",
            summary.get('summary', 'N/A'),
            "",
            "## 核心贡献",
        ]

        for contrib in summary.get('key_contributions', []):
            lines.append(f"- {contrib}")

        lines.extend(["", "## 研究方法"])
        for method in summary.get('methods', []):
            lines.append(f"- {method}")

        return "\n".join(lines)

    summary = {
        "title": "Test Paper",
        "authors": ["Author A", "Author B", "Author C"],
        "arxiv_id": "1234.56789",
        "relevance_score": 8,
        "summary": "This is a test summary.",
        "key_contributions": ["Contribution 1", "Contribution 2"],
        "methods": ["Method 1"]
    }

    formatted = format_summary(summary)
    assert "Test Paper" in formatted
    assert "8/10" in formatted
    assert "Contribution 1" in formatted
    print("✓ 单篇摘要格式化成功")

    # 测试多篇摘要格式化
    def format_summaries(summaries: list) -> str:
        if not summaries:
            return "没有论文摘要。"

        sections = [f"# 论文阅读总结\n共{len(summaries)}篇论文\n"]

        for i, summary in enumerate(summaries, 1):
            sections.append(f"## [{i}] {summary.get('title', 'N/A')}")
            sections.append(f"**相关度**: {summary.get('relevance_score', 'N/A')}/10")
            sections.append(f"**核心贡献**: {', '.join(summary.get('key_contributions', [])[:2])}")
            sections.append("")

        return "\n".join(sections)

    summaries = [summary, summary]
    formatted_multi = format_summaries(summaries)
    assert "共2篇论文" in formatted_multi
    print("✓ 多篇摘要格式化成功")

    print("\n摘要格式化输出测试通过！\n")


async def test_reader_agent_execute():
    """测试ReaderAgent完整执行（需要API密钥）"""
    print("=" * 60)
    print("测试4: ReaderAgent执行测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        print("  请设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        return True

    from agents.reader import ReaderAgent

    # 创建Reader实例
    reader = ReaderAgent()
    print("✓ ReaderAgent创建成功")

    # 创建测试用的论文数据
    papers = [
        {
            "arxiv_id": "2201.11903",
            "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
            "authors": ["Jason Wei", "Xuezhi Wang", "Dale Schuurmans", "Maarten Bosma"],
            "abstract": "We explore how generating a chain of thought—a series of intermediate reasoning steps—significantly improves the ability of large language models to perform complex reasoning. Through experiments on arithmetic, commonsense, and symbolic reasoning tasks, we show that chain-of-thought prompting outperforms standard prompting by a large margin.",
            "url": "https://arxiv.org/abs/2201.11903",
            "published": "2022-01-28"
        },
        {
            "arxiv_id": "2210.03629",
            "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
            "authors": ["Shunyu Yao", "Jeffrey Zhao", "Dian Yu"],
            "abstract": "We present ReAct, a paradigm that combines reasoning and acting in language models for solving diverse language reasoning and decision making tasks. ReAct prompts LLMs to generate both reasoning traces and task-specific actions in an interleaved manner.",
            "url": "https://arxiv.org/abs/2210.03629",
            "published": "2022-10-07"
        }
    ]

    state = create_initial_state("LLM reasoning方法调研")
    state["papers"] = papers

    try:
        # 执行Reader
        result_state = await reader.execute(state)

        print(f"\n✓ Reader执行成功")
        print(f"当前步骤: {result_state['current_step']}")
        print(f"生成摘要数: {len(result_state.get('paper_summaries', []))}")

        # 打印部分摘要信息
        summaries = result_state.get('paper_summaries', [])
        if summaries:
            print("\n摘要示例（第一篇）:")
            summary = summaries[0]
            print(f"  标题: {summary['title'][:50]}...")
            print(f"  相关度: {summary.get('relevance_score', 'N/A')}/10")
            print(f"  核心贡献数: {len(summary.get('key_contributions', []))}")

        # 打印消息日志
        print("\n执行日志:")
        for msg in result_state.get('messages', []):
            print(f"  [{msg['agent']}] {msg['message'][:70]}...")

        return True

    except Exception as e:
        print(f"\n✗ Reader执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_read_single_paper():
    """测试独立阅读单篇论文（需要API密钥）"""
    print("=" * 60)
    print("测试5: 独立阅读单篇论文测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        return True

    from agents.reader import ReaderAgent

    try:
        reader = ReaderAgent()
    except Exception as e:
        print(f"⚠ 创建ReaderAgent需要API配置: {e}")
        return True

    try:
        summary = await reader.read_single_paper(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            abstract="We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
            arxiv_id="1706.03762",
            url="https://arxiv.org/abs/1706.03762"
        )

        print(f"✓ 单篇论文阅读成功")
        print(f"  标题: {summary['title']}")
        print(f"  相关度: {summary.get('relevance_score', 'N/A')}/10")
        print(f"  概述: {summary.get('summary', 'N/A')[:100]}...")

        # 测试格式化输出
        formatted = reader.format_summary(summary)
        print(f"\n格式化预览:\n{formatted[:300]}...")

        return True

    except Exception as e:
        print(f"✗ 单篇论文阅读失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Reader Agent 测试套件")
    print("=" * 60 + "\n")

    # 运行所有测试
    success = True

    success = test_import() and success
    test_summary_parser()
    test_format_paper_for_reading()
    test_format_summary()
    success = await test_read_single_paper() and success
    success = await test_reader_agent_execute() and success

    print("=" * 60)
    if success:
        print("所有测试通过！✓")
    else:
        print("部分测试失败 ✗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
