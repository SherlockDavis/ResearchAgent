"""项目入口文件"""
import asyncio
import argparse
import os
from config import get_settings
from utils.logger import logger
from workflow import ResearchWorkflow


async def run_research_workflow(query: str, model: str = None, max_papers: int = 10):
    """运行完整研究流程

    Args:
        query: 研究问题
        model: 模型名称（可选）
        max_papers: 最大阅读论文数量，默认10篇

    Returns:
        研究状态字典
    """
    settings = get_settings()
    logger.info(f"Starting research for query: {query}")
    logger.info(f"Using model: {model or settings.DEFAULT_MODEL}")
    logger.info(f"Max papers to read: {max_papers}")

    # 设置模型（如果指定）
    if model:
        os.environ["DEFAULT_MODEL"] = model

    # 创建工作流
    workflow = ResearchWorkflow()

    try:
        # 运行工作流
        result = await workflow.run(query, max_papers=max_papers)

        # 获取执行摘要
        summary = workflow.get_execution_summary(result)
        logger.info(f"Research completed: {summary}")

        return result

    except Exception as e:
        logger.error(f"Research workflow failed: {e}")
        raise


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Research Agent - 自动化科研助手")
    parser.add_argument(
        "query",
        type=str,
        help="研究问题，例如：'LLM reasoning最新进展'",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="使用的模型名称",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="报告输出文件路径",
    )
    parser.add_argument(
        "--max-papers",
        "-n",
        type=int,
        default=10,
        help="最大阅读论文数量，默认10篇",
    )

    args = parser.parse_args()

    # 运行研究
    try:
        result = asyncio.run(run_research_workflow(args.query, args.model, args.max_papers))

        # 打印执行摘要
        print("\n" + "=" * 60)
        print("研究执行摘要")
        print("=" * 60)
        print(f"研究问题: {result.get('query', 'N/A')}")
        print(f"最终状态: {result.get('current_step', 'N/A')}")
        print(f"检索论文数: {len(result.get('papers', []))}")
        print(f"阅读论文数: {len(result.get('paper_summaries', []))}")

        if result.get('report'):
            report_preview = result['report'][:300] + "..."
            print(f"\n报告预览:\n{report_preview}")

            # 保存报告（如果指定输出路径）
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result['report'])
                print(f"\n报告已保存到: {args.output}")

        print("=" * 60)

    except Exception as e:
        logger.error(f"Research failed: {e}")
        print(f"\n研究失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()
