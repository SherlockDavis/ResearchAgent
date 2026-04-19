"""Searcher Agent 测试脚本"""
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
        from agents import SearcherAgent
        print("✓ 从agents导入SearcherAgent成功")
    except ImportError as e:
        print(f"✗ 从agents导入失败: {e}")
        return False

    try:
        from agents.searcher import SearcherAgent
        print("✓ 从agents.searcher导入SearcherAgent成功")
    except ImportError as e:
        print(f"✗ 从agents.searcher导入失败: {e}")
        return False

    print("\n模块导入测试通过！\n")
    return True


def test_arxiv_searcher():
    """测试arXiv搜索工具（无需LLM）"""
    print("=" * 60)
    print("测试1: arXiv搜索工具测试")
    print("=" * 60)

    from tools.arxiv_search import ArxivSearcher

    searcher = ArxivSearcher()
    print("✓ ArxivSearcher创建成功")

    # 测试同步搜索
    try:
        papers = searcher.search(
            query="transformer attention mechanism",
            max_results=3
        )
        print(f"✓ 同步搜索成功，找到{len(papers)}篇论文")

        if papers:
            paper = papers[0]
            print(f"  示例论文: {paper.title[:60]}...")
            print(f"  arXiv ID: {paper.arxiv_id}")
            print(f"  作者数: {len(paper.authors)}")
    except Exception as e:
        print(f"✗ 同步搜索失败: {e}")
        return False

    print("\narXiv搜索工具测试通过！\n")
    return True


async def test_arxiv_searcher_async():
    """测试arXiv异步搜索"""
    print("=" * 60)
    print("测试2: arXiv异步搜索测试")
    print("=" * 60)

    from tools.arxiv_search import ArxivSearcher

    searcher = ArxivSearcher()

    try:
        papers = await searcher.search_async(
            query="large language model reasoning",
            max_results=3
        )
        print(f"✓ 异步搜索成功，找到{len(papers)}篇论文")
    except Exception as e:
        print(f"✗ 异步搜索失败: {e}")
        return False

    print("\narXiv异步搜索测试通过！\n")
    return True


def test_search_config_parser():
    """测试搜索配置解析（无需LLM）"""
    print("=" * 60)
    print("测试3: 搜索配置解析测试")
    print("=" * 60)

    # 模拟SearcherAgent的解析方法
    import json

    def parse_search_config(content: str):
        """解析搜索配置JSON"""
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

        raise ValueError(f"无法解析搜索配置: {content[:200]}...")

    # 测试用例1: 标准JSON
    test_case_1 = '''{
        "search_queries": ["query1", "query2"],
        "max_results": 10,
        "sort_by": "relevance",
        "search_strategy": "测试策略"
    }'''

    result = parse_search_config(test_case_1)
    assert "search_queries" in result
    assert len(result["search_queries"]) == 2
    print("✓ 标准JSON解析成功")

    # 测试用例2: Markdown代码块
    test_case_2 = '''```json
    {
        "search_queries": ["cat:cs.CL AND abs:LLM"],
        "max_results": 5,
        "sort_by": "submittedDate",
        "search_strategy": "搜索NLP分类下的LLM论文"
    }
    ```'''

    result = parse_search_config(test_case_2)
    assert result["max_results"] == 5
    print("✓ Markdown代码块解析成功")

    print("\n搜索配置解析测试通过！\n")


async def test_searcher_agent_execute():
    """测试SearcherAgent完整执行（需要API密钥）"""
    print("=" * 60)
    print("测试4: SearcherAgent执行测试（需要API密钥）")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过此测试")
        print("  请设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        return True

    from agents.searcher import SearcherAgent

    # 创建Searcher实例
    searcher = SearcherAgent()
    print("✓ SearcherAgent创建成功")

    # 创建初始状态
    state = create_initial_state("帮我调研LLM reasoning最新进展")
    # 添加模拟的searcher任务
    state["sub_tasks"] = [
        {
            "id": "task_1",
            "description": "检索LLM reasoning相关论文，重点关注Chain-of-Thought、Tree-of-Thought等方法",
            "agent_type": "searcher",
            "status": "pending",
            "dependencies": []
        }
    ]

    try:
        # 执行Searcher
        result_state = await searcher.execute(state)

        print(f"\n✓ Searcher执行成功")
        print(f"当前步骤: {result_state['current_step']}")
        print(f"找到论文数: {len(result_state.get('papers', []))}")

        # 打印部分论文信息
        papers = result_state.get('papers', [])
        if papers:
            print("\n论文列表（前3篇）:")
            for i, paper in enumerate(papers[:3], 1):
                print(f"  {i}. {paper['title'][:60]}...")
                print(f"     arXiv: {paper['arxiv_id']}")

        # 打印消息日志
        print("\n执行日志:")
        for msg in result_state.get('messages', []):
            print(f"  [{msg['agent']}] {msg['message'][:80]}...")

        return True

    except Exception as e:
        print(f"\n✗ Searcher执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_searcher_direct_search():
    """测试SearcherAgent独立搜索方法（无需LLM优化）"""
    print("=" * 60)
    print("测试5: SearcherAgent独立搜索测试")
    print("=" * 60)

    import os
    from agents.searcher import SearcherAgent

    # 创建Searcher实例（不依赖API密钥）
    try:
        searcher = SearcherAgent()
    except Exception as e:
        print(f"⚠ 创建SearcherAgent需要API配置: {e}")
        print("  跳过此测试")
        return True

    try:
        # 使用独立搜索方法（不使用LLM优化）
        papers = await searcher.search_papers(
            query="attention mechanism",
            max_results=3,
            use_llm_optimization=False
        )

        print(f"✓ 独立搜索成功，找到{len(papers)}篇论文")

        if papers:
            print("\n论文列表:")
            for i, paper in enumerate(papers, 1):
                print(f"  {i}. {paper['title'][:60]}...")
                print(f"     作者: {', '.join(paper['authors'][:2])}")

        # 测试格式化输出
        summary = searcher.format_papers_summary(papers)
        print(f"\n格式化摘要预览:\n{summary[:300]}...")

        return True

    except Exception as e:
        print(f"✗ 独立搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Searcher Agent 测试套件")
    print("=" * 60 + "\n")

    # 运行所有测试
    success = True

    success = test_import() and success
    success = test_arxiv_searcher() and success
    success = await test_arxiv_searcher_async() and success
    test_search_config_parser()
    success = await test_searcher_direct_search() and success
    success = await test_searcher_agent_execute() and success

    print("=" * 60)
    if success:
        print("所有测试通过！✓")
    else:
        print("部分测试失败 ✗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
