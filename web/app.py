"""Gradio Web界面 - ResearchAgent可视化交互"""
import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional
from datetime import datetime
import json

import gradio as gr

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow import ResearchWorkflow
from utils.state import StateValidator, get_state_summary
from utils.logger import logger
from utils.docx_exporter import markdown_to_docx


class ResearchApp:
    """ResearchAgent Gradio应用"""

    def __init__(self):
        self.workflow: Optional[ResearchWorkflow] = None
        self.current_state = None
        # 生成统一的时间戳，用于日志文件和报告文件名
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 使用统一时间戳初始化logger
        from utils.logger import setup_logger
        self.logger = setup_logger("research_agent_web", timestamp=self.timestamp)
        


    def initialize_workflow(self) -> bool:
        """初始化工作流"""
        try:
            self.workflow = ResearchWorkflow()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize workflow: {e}")
            return False

    def _get_progress_html(self, step_name: str, message: str) -> str:
        """生成步骤进行中的进度HTML"""
        return f"""
        <div style='text-align:center;padding:30px;'>
            <div style='display:inline-block;width:40px;height:40px;border:3px solid #e0f2fe;border-top:3px solid #0ea5e9;border-radius:50%;animation:spin 1s linear infinite;'></div>
            <p style='margin-top:16px;color:#0ea5e9;font-size:16px;'>{message}</p>
        </div>
        <style>@keyframes spin {{0% {{transform:rotate(0deg);}} 100% {{transform:rotate(360deg);}}}}</style>
        """

    def _toggle_btn_html(self, label_expand="🔽 展开查看全部", label_collapse="🔼 收起"):
        """生成内嵌展开/折叠按钮的HTML"""
        return f"""<div style="text-align:center;margin-top:12px;">
            <button onclick="var p=this.closest('.step-result');var c=p.querySelector('.sr-collapsed');var f=p.querySelector('.sr-full');if(f.style.display==='none'){{f.style.display='block';c.style.display='none';this.innerHTML='{label_collapse}';}}else{{f.style.display='none';c.style.display='block';this.innerHTML='{label_expand}';}}"
            style="background:linear-gradient(135deg,#0ea5e9,#0284c7);color:white;border:none;border-radius:8px;padding:8px 24px;font-weight:600;cursor:pointer;transition:all 0.2s;">{label_expand}</button>
        </div>"""

    def _format_subtasks(self, sub_tasks: list) -> str:
        """格式化子任务为HTML展示（含内嵌展开/折叠）"""
        if not sub_tasks:
            return "<p style='text-align:center;color:#666;'>暂无子任务</p>"
        
        first_task = sub_tasks[0]
        status_color = {"pending": "#fbbf24", "completed": "#22c55e", "failed": "#ef4444"}.get(
            first_task.get("status", "pending"), "#fbbf24"
        )
        collapsed = f"""
            <div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;text-align:left;'>
                <div style='display:flex;align-items:center;gap:8px;'>
                    <span style='background:{status_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;'>
                        {first_task.get("status", "pending")}
                    </span>
                    <span style='font-weight:600;color:#1e293b;'>任务 1: {first_task.get("agent_type", "unknown")}</span>
                    <span style='color:#64748b;font-size:14px;flex:1;'>{first_task.get("description", "")[:80]}...</span>
                    <span style='color:#0ea5e9;font-size:13px;'>共{len(sub_tasks)}个子任务</span>
                </div>
            </div>
        """
        
        full = ""
        for i, task in enumerate(sub_tasks, 1):
            sc = {"pending": "#fbbf24", "completed": "#22c55e", "failed": "#ef4444"}.get(
                task.get("status", "pending"), "#fbbf24"
            )
            full += f"""
            <div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;margin:8px 0;text-align:left;'>
                <div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>
                    <span style='background:{sc};color:white;padding:2px 8px;border-radius:4px;font-size:12px;'>
                        {task.get("status", "pending")}
                    </span>
                    <span style='font-weight:600;color:#1e293b;'>任务 {i}: {task.get("agent_type", "unknown")}</span>
                </div>
                <p style='margin:0;color:#475569;font-size:14px;'>{task.get("description", "")}</p>
            </div>
            """
        
        return f"""<div class='step-result' style='max-width:800px;margin:0 auto;'>
            <div class='sr-collapsed'>{collapsed}</div>
            <div class='sr-full' style='display:none;'>{full}</div>
            {self._toggle_btn_html()}
        </div>"""

    def _format_papers(self, papers: list) -> str:
        """格式化论文列表为HTML展示（含内嵌展开/折叠）"""
        if not papers:
            return "<p style='text-align:center;color:#666;'>暂无论文</p>"
        
        first_paper = papers[0]
        authors = first_paper.get("authors", [])
        author_str = ", ".join(authors[:2]) + (" et al." if len(authors) > 2 else "")
        collapsed = f"""
            <div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;text-align:left;'>
                <div style='display:flex;align-items:center;gap:12px;'>
                    <span style='background:#0ea5e9;color:white;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;'>1</span>
                    <span style='flex:1;font-weight:600;color:#1e293b;'>{first_paper.get("title", "")[:60]}...</span>
                    <span style='color:#64748b;font-size:13px;'>👤 {author_str}</span>
                    <span style='color:#0ea5e9;font-size:13px;font-weight:600;'>共{len(papers)}篇论文</span>
                </div>
            </div>
        """
        
        full = f"<p style='text-align:center;color:#0ea5e9;font-weight:600;margin-bottom:16px;'>共检索到 {len(papers)} 篇论文</p>"
        for i, paper in enumerate(papers, 1):
            a = paper.get("authors", [])
            a_str = ", ".join(a[:3]) + (" et al." if len(a) > 3 else "")
            full += f"""
            <div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;margin:8px 0;text-align:left;'>
                <div style='display:flex;align-items:flex-start;gap:12px;'>
                    <span style='background:#0ea5e9;color:white;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;min-width:36px;text-align:center;'>{i}</span>
                    <div style='flex:1;'>
                        <p style='margin:0 0 6px 0;font-weight:600;color:#1e293b;font-size:15px;'>{paper.get("title", "")}</p>
                        <p style='margin:0 0 4px 0;color:#64748b;font-size:13px;'>👤 {a_str}</p>
                        <p style='margin:0;color:#94a3b8;font-size:12px;'>📅 {paper.get("published", "")[:10] if paper.get("published") else "N/A"}</p>
                    </div>
                </div>
            </div>
            """
        
        return f"""<div class='step-result' style='max-width:900px;margin:0 auto;'>
            <div class='sr-collapsed'>{collapsed}</div>
            <div class='sr-full' style='display:none;'>{full}</div>
            {self._toggle_btn_html()}
        </div>"""

    def _format_summaries(self, summaries: list) -> str:
        """格式化论文摘要为HTML展示（含内嵌展开/折叠）"""
        if not summaries:
            return "<p style='text-align:center;color:#666;'>暂无阅读结果</p>"
        
        first = summaries[0]
        score = first.get("relevance_score", 0)
        score_color = "#22c55e" if score >= 8 else "#f59e0b" if score >= 5 else "#ef4444"
        collapsed = f"""
            <div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;text-align:left;'>
                <div style='display:flex;align-items:center;gap:12px;'>
                    <span style='background:#8b5cf6;color:white;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;'>1</span>
                    <span style='flex:1;font-weight:600;color:#1e293b;'>{first.get("title", "")[:50]}...</span>
                    <span style='background:{score_color};color:white;padding:4px 12px;border-radius:12px;font-size:13px;font-weight:600;'>相关度: {score}/10</span>
                    <span style='color:#0ea5e9;font-size:13px;font-weight:600;'>共{len(summaries)}篇</span>
                </div>
            </div>
        """
        
        full = f"<p style='text-align:center;color:#0ea5e9;font-weight:600;margin-bottom:16px;'>已阅读 {len(summaries)} 篇论文</p>"
        for i, summary in enumerate(summaries, 1):
            sc = summary.get("relevance_score", 0)
            sc_color = "#22c55e" if sc >= 8 else "#f59e0b" if sc >= 5 else "#ef4444"
            full += f"""
            <div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:16px;margin:12px 0;text-align:left;'>
                <div style='display:flex;align-items:center;gap:12px;margin-bottom:10px;'>
                    <span style='background:#8b5cf6;color:white;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;'>{i}</span>
                    <span style='flex:1;font-weight:600;color:#1e293b;'>{summary.get("title", "")}</span>
                    <span style='background:{sc_color};color:white;padding:4px 12px;border-radius:12px;font-size:13px;font-weight:600;'>相关度: {sc}/10</span>
                </div>
                <p style='margin:8px 0;color:#475569;font-size:14px;line-height:1.6;'>{summary.get("summary", "")[:200]}...</p>
                <div style='margin-top:10px;padding-top:10px;border-top:1px solid #e2e8f0;'>
                    <p style='margin:0;color:#64748b;font-size:13px;'><strong>核心贡献:</strong> {", ".join(summary.get("key_contributions", [])[:2])}</p>
                </div>
            </div>
            """
        
        return f"""<div class='step-result' style='max-width:900px;margin:0 auto;'>
            <div class='sr-collapsed'>{collapsed}</div>
            <div class='sr-full' style='display:none;'>{full}</div>
            {self._toggle_btn_html()}
        </div>"""

    def _format_analysis(self, analysis: dict) -> str:
        """格式化分析结果为HTML展示（含内嵌展开/折叠）"""
        if not analysis:
            return "<p style='text-align:center;color:#666;'>暂无分析结果</p>"
        
        overview = analysis.get("overview", "")[:100] + "..."
        insights = analysis.get("key_insights", [])
        
        collapsed = f"""
            <div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;text-align:left;'>
                <p style='margin:0;color:#1e293b;font-size:14px;'><strong>📊 领域全景:</strong> {overview}</p>
                {f"<p style='margin:8px 0 0 0;color:#0ea5e9;font-size:13px;'>💡 关键洞察: {len(insights)}条</p>" if insights else ""}
            </div>
        """
        
        full = ""
        if analysis.get("overview"):
            full += f"""
            <div style='background:linear-gradient(135deg,#0ea5e9 0%,#0284c7 100%);color:white;border-radius:12px;padding:20px;margin:16px 0;text-align:left;'>
                <h4 style='margin:0 0 12px 0;font-size:16px;'>📊 领域全景</h4>
                <p style='margin:0;font-size:14px;line-height:1.7;'>{analysis.get("overview", "")}</p>
            </div>
            """
        if insights:
            full += "<div style='margin:16px 0;'><h4 style='color:#1e293b;margin-bottom:12px;'>💡 关键洞察</h4>"
            for i, insight in enumerate(insights[:4], 1):
                full += f"""
                <div style='background:#f0f9ff;border-left:4px solid #0ea5e9;padding:12px 16px;margin:8px 0;text-align:left;border-radius:0 8px 8px 0;'>
                    <p style='margin:0;color:#0c4a6e;font-size:14px;line-height:1.6;'><strong>洞察 {i}:</strong> {insight[:150]}...</p>
                </div>
                """
            full += "</div>"
        trends = analysis.get("trends", [])
        if trends:
            full += "<div style='margin:16px 0;'><h4 style='color:#1e293b;margin-bottom:12px;'>📈 发展趋势</h4>"
            for i, trend in enumerate(trends[:3], 1):
                full += f"""
                <div style='background:#e0f2fe;border-left:4px solid #0ea5e9;padding:12px 16px;margin:8px 0;text-align:left;border-radius:0 8px 8px 0;'>
                    <p style='margin:0;color:#075985;font-size:14px;line-height:1.6;'><strong>趋势 {i}:</strong> {trend[:120]}...</p>
                </div>
                """
            full += "</div>"
        
        return f"""<div class='step-result' style='max-width:900px;margin:0 auto;'>
            <div class='sr-collapsed'>{collapsed}</div>
            <div class='sr-full' style='display:none;'>{full}</div>
            {self._toggle_btn_html()}
        </div>"""

    def _format_writer(self, report: str) -> str:
        """格式化Writer结果为HTML展示（含内嵌展开/折叠）"""
        if not report:
            return "<p style='text-align:center;color:#666;'>暂无报告</p>"
        
        # 提取摘要部分
        try:
            abstract_match = report.split("## 摘要")[1].split("##")[0] if "## 摘要" in report else report[:200]
            abstract = abstract_match.strip()[:150] + "..."
        except Exception:
            abstract = report[:200] + "..."
        
        collapsed = f"""
            <div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;text-align:left;'>
                <p style='margin:0;color:#1e293b;font-size:14px;'><strong>📝 摘要:</strong> {abstract}</p>
                <p style='margin:8px 0 0 0;color:#0ea5e9;font-size:13px;'>📄 报告长度: {len(report)} 字符</p>
            </div>
        """
        
        full = f"""
            <div style='background:linear-gradient(135deg,#0ea5e9 0%,#0284c7 100%);color:white;border-radius:12px;padding:20px;text-align:center;'>
                <h3 style='margin:0 0 12px 0;'>✅ 报告生成完成</h3>
                <p style='margin:0;font-size:14px;'>报告长度: {len(report)} 字符 | 包含摘要、引言、方法、发现、讨论、结论等章节</p>
            </div>
        """
        
        return f"""<div class='step-result' style='max-width:900px;margin:0 auto;'>
            <div class='sr-collapsed'>{collapsed}</div>
            <div class='sr-full' style='display:none;'>{full}</div>
            {self._toggle_btn_html()}
        </div>"""

    async def run_research(
        self,
        query: str,
        max_papers: int = 10,
    ) -> AsyncGenerator[tuple, None]:
        """运行研究流程并生成进度更新

        Args:
            query: 研究问题
            max_papers: 最大阅读论文数量

        Yields:
            8-tuple: (总进度, planner_html, searcher_html, reader_html, analyst_html, writer_html, log_text, report_text)
        """
        if not query or not query.strip():
            yield 0, "", "", "", "", "", "错误: 研究问题不能为空", ""
            return

        # 初始化工作流
        if self.workflow is None:
            if not self.initialize_workflow():
                yield 0, "", "", "", "", "", "错误: 无法初始化工作流，请检查配置", ""
                return

        logs = []

        def log_callback(message: str):
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

        # 初始化各步骤显示
        planner_html = "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>"
        searcher_html = "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>"
        reader_html = "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>"
        analyst_html = "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>"
        writer_html = "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>"

        try:
            log_callback(f"开始研究: {query}")
            log_callback(f"最大论文数量: {max_papers}篇")

            state = None

            # ===== Step 1: Planner =====
            log_callback("开始: 任务规划中...")
            planner_html = self._get_progress_html("planner", "正在分析研究问题并生成子任务...")
            yield 10, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""

            state = await self.workflow._planner_node(
                {"query": query, "sub_tasks": [], "papers": [],
                 "paper_summaries": [], "analysis": {}, "report": "",
                 "current_step": "init", "messages": [], "errors": [],
                 "start_time": datetime.now(), "end_time": None,
                 "max_papers": max_papers}
            )

            sub_tasks = state.get("sub_tasks", [])
            planner_html = self._format_subtasks(sub_tasks)
            log_callback(f"完成: 任务规划，生成{len(sub_tasks)}个子任务")
            yield 20, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""
            await asyncio.sleep(0.1)

            # ===== Step 2: Searcher =====
            log_callback("开始: 检索论文中...")
            searcher_html = self._get_progress_html("searcher", "正在检索相关论文...")
            yield 30, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""

            state = await self.workflow._searcher_node(state)

            papers = state.get("papers", [])
            searcher_html = self._format_papers(papers)
            log_callback(f"完成: 检索论文，共找到{len(papers)}篇")
            yield 40, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""
            await asyncio.sleep(0.1)

            # ===== Step 3: Reader =====
            log_callback("开始: 阅读论文中...")
            reader_html = self._get_progress_html("reader", "正在阅读并分析论文...")
            yield 50, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""

            state = await self.workflow._reader_node(state)

            summaries = state.get("paper_summaries", [])
            reader_html = self._format_summaries(summaries)
            log_callback(f"完成: 阅读论文，共生成{len(summaries)}篇摘要")
            yield 60, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""
            await asyncio.sleep(0.1)

            # ===== Step 4: Analyst =====
            log_callback("开始: 分析对比中...")
            analyst_html = self._get_progress_html("analyst", "正在进行横向对比分析...")
            yield 70, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""

            state = await self.workflow._analyst_node(state)

            analysis = state.get("analysis", {})
            analyst_html = self._format_analysis(analysis)
            log_callback("完成: 分析对比")
            yield 80, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""
            await asyncio.sleep(0.1)

            # ===== Step 5: Writer =====
            log_callback("开始: 生成报告中...")
            writer_html = self._get_progress_html("writer", "正在撰写综述报告...")
            yield 90, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""

            state = await self.workflow._writer_node(state)

            report = state.get("report", "")
            writer_html = self._format_writer(report)
            log_callback("完成: 生成报告")
            log_callback("研究完成!")

            if state:
                self.current_state = state

            yield 100, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), report

        except Exception as e:
            error_msg = f"研究过程中出错: {str(e)}"
            logger.error(error_msg)
            log_callback(f"错误: {error_msg}")
            yield 0, planner_html, searcher_html, reader_html, analyst_html, writer_html, "\n".join(logs), ""

    def save_report(self, report: str) -> tuple:
        """保存报告到文件并提供下载

        Args:
            report: 报告内容

        Returns:
            (保存结果信息, 文件路径)
        """
        if not report or not report.strip():
            return "没有可保存的报告", None

        try:
            from utils.state import StateManager
            manager = StateManager()

            # 使用统一的时间戳生成报告文件名
            filename = f"research_report_{self.timestamp}.docx"
            filepath = manager.storage_dir / filename

            markdown_to_docx(report, str(filepath))

            return f"✅ 报告已保存: {filename}", str(filepath)
        except Exception as e:
            return f"❌ 保存失败: {e}", None

    def get_execution_info(self) -> str:
        """获取执行信息"""
        if self.current_state is None:
            return "暂无执行信息"

        summary = get_state_summary(self.current_state)

        info_lines = [
            "## 执行摘要",
            f"**研究问题**: {summary['query']}",
            f"**最终状态**: {summary['current_step']}",
            f"**执行时间**: {summary['duration_seconds']:.2f}秒" if summary['duration_seconds'] else "**执行时间**: N/A",
            f"**检索论文数**: {summary['papers_count']}",
            f"**阅读论文数**: {summary['summaries_count']}",
            f"**生成报告**: {'✅' if summary['has_report'] else '❌'}",
            f"**消息数**: {summary['message_count']}",
            f"**错误数**: {summary['error_count']}",
        ]

        return "\n\n".join(info_lines)


def create_ui() -> gr.Blocks:
    """创建Gradio界面 - 单列居中顺序布局

    Returns:
        Gradio Blocks界面
    """
    app = ResearchApp()

    custom_css = """
    .step-section {
        max-width: 1000px;
        margin: 20px auto;
        padding: 24px;
        border-radius: 16px;
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.1), 0 2px 4px -1px rgba(14, 165, 233, 0.06);
        border: 1px solid #bae6fd;
    }
    .step-header {
        text-align: center;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 2px solid #bae6fd;
    }
    .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
        color: white;
        border-radius: 50%;
        font-weight: 700;
        font-size: 18px;
        margin-right: 12px;
    }
    .step-title {
        font-size: 20px;
        font-weight: 600;
        color: #0c4a6e;
    }
    .expand-btn {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 24px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: all 0.2s !important;
    }
    .expand-btn:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3) !important;
    }
    """

    with gr.Blocks(title="ResearchAgent - 自动化科研助手", css=custom_css, theme=gr.themes.Soft()) as demo:
        # 标题区域 - 淡蓝色主题
        gr.Markdown("""
        <div style="text-align:center;padding:40px 20px;background:linear-gradient(135deg,#0ea5e9 0%,#0284c7 100%);border-radius:16px;margin-bottom:30px;">
            <h1 style="color:white;margin:0;font-size:36px;">🔬 ResearchAgent</h1>
            <p style="color:rgba(255,255,255,0.9);margin:12px 0 0 0;font-size:18px;">自动化科研助手 - 多Agent协作完成文献综述</p>
        </div>
        """)

        # 输入配置区域
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-number">✏️</span>
                <span class="step-title">研究配置</span>
            </div>
            """)
            
            query_input = gr.Textbox(
                label="研究问题",
                placeholder="例如：LLM reasoning最新进展、RAG技术综述、多模态学习前沿...",
                lines=3,
                max_lines=5,
            )
            
            gr.Markdown("<p style='color:#0c4a6e;margin:12px 0;'>💡 点击快速填充示例问题：</p>")
            examples = gr.Examples(
                examples=[
                    ["LLM reasoning最新进展"],
                    ["RAG检索增强生成技术综述"],
                    ["Chain-of-Thought prompting方法对比"],
                    ["多模态大模型研究现状"],
                    ["AI Agent自主决策能力分析"],
                ],
                inputs=[query_input],
                label=None,
            )
            
            max_papers_slider = gr.Slider(
                label="最大阅读论文数量",
                minimum=1,
                maximum=30,
                value=10,
                step=1,
            )
            
            with gr.Row():
                submit_btn = gr.Button("🚀 开始研究", variant="primary", scale=2)
                clear_btn = gr.Button("🔄 清空", variant="secondary", scale=1)

        # 总进度条
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-title">📊 总体进度</span>
            </div>
            """)
            total_progress = gr.Slider(
                label="",
                minimum=0,
                maximum=100,
                value=0,
                interactive=False,
            )

        # Step 1: Planner
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-number">1</span>
                <span class="step-title">📋 Planner - 任务规划</span>
            </div>
            <p style="text-align:center;color:#0c4a6e;margin-bottom:16px;">分析研究问题，拆解为可执行的子任务</p>
            """)
            planner_output = gr.HTML(value="<p style='text-align:center;color:#94a3b8;'>等待开始...</p>")

        # Step 2: Searcher
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-number">2</span>
                <span class="step-title">🔍 Searcher - 文献检索</span>
            </div>
            <p style="text-align:center;color:#0c4a6e;margin-bottom:16px;">检索arXiv相关论文</p>
            """)
            searcher_output = gr.HTML(value="<p style='text-align:center;color:#94a3b8;'>等待开始...</p>")

        # Step 3: Reader
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-number">3</span>
                <span class="step-title">📖 Reader - 论文阅读</span>
            </div>
            <p style="text-align:center;color:#0c4a6e;margin-bottom:16px;">精读论文并提取核心信息、评估相关度</p>
            """)
            reader_output = gr.HTML(value="<p style='text-align:center;color:#94a3b8;'>等待开始...</p>")

        # Step 4: Analyst
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-number">4</span>
                <span class="step-title">🔬 Analyst - 对比分析</span>
            </div>
            <p style="text-align:center;color:#0c4a6e;margin-bottom:16px;">横向对比多篇论文，提炼洞察与趋势</p>
            """)
            analyst_output = gr.HTML(value="<p style='text-align:center;color:#94a3b8;'>等待开始...</p>")

        # Step 5: Writer
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-number">5</span>
                <span class="step-title">📝 Writer - 报告生成</span>
            </div>
            <p style="text-align:center;color:#0c4a6e;margin-bottom:16px;">撰写结构化综述报告</p>
            """)
            writer_output = gr.HTML(value="<p style='text-align:center;color:#94a3b8;'>等待开始...</p>")

        # 最终报告区域
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-title">📄 最终研究报告</span>
            </div>
            """)
            report_output = gr.Markdown(value="报告将在此显示...")
            
            with gr.Row():
                save_btn = gr.Button("💾 保存报告", variant="primary")
                info_btn = gr.Button("ℹ️ 查看执行摘要", variant="secondary")
            
            # 下载文件组件
            download_file = gr.File(label="下载报告", visible=False)
            save_result = gr.Textbox(label="保存结果", interactive=False)
            info_output = gr.Markdown(visible=False)

        # 执行日志
        with gr.Column(elem_classes="step-section"):
            gr.Markdown("""
            <div class="step-header">
                <span class="step-title">📋 执行日志</span>
            </div>
            """)
            log_output = gr.Textbox(
                label="",
                lines=10,
                max_lines=15,
                interactive=False,
                autoscroll=True,
            )

        # 事件绑定
        submit_btn.click(
            fn=app.run_research,
            inputs=[query_input, max_papers_slider],
            outputs=[
                total_progress,
                planner_output, searcher_output, reader_output, analyst_output, writer_output,
                log_output, report_output
            ],
        )

        clear_btn.click(
            fn=lambda: (
                0,
                "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>",
                "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>",
                "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>",
                "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>",
                "<p style='text-align:center;color:#94a3b8;'>等待开始...</p>",
                "",
                "报告将在此显示...",
                None
            ),
            inputs=[],
            outputs=[
                total_progress,
                planner_output, searcher_output, reader_output, analyst_output, writer_output,
                log_output, report_output,
                download_file
            ],
        )

        # 保存报告并提供下载
        def handle_save_report(report_text):
            result_msg, filepath = app.save_report(report_text)
            if filepath:
                return result_msg, gr.update(value=filepath, visible=True)
            return result_msg, gr.update(visible=False)

        save_btn.click(
            fn=handle_save_report,
            inputs=[report_output],
            outputs=[save_result, download_file],
        )

        def toggle_info():
            info = app.get_execution_info()
            return {info_output: gr.Markdown(visible=True, value=info)}

        info_btn.click(
            fn=toggle_info,
            inputs=[],
            outputs=[info_output],
        )

    return demo


def launch_app(
    share: bool = False,
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
):
    """启动Gradio应用

    Args:
        share: 是否创建公共链接
        server_name: 服务器地址
        server_port: 服务器端口
    """
    demo = create_ui()
    demo.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        show_error=True,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ResearchAgent Web界面")
    parser.add_argument(
        "--share",
        action="store_true",
        help="创建公共共享链接",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="服务器地址",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="服务器端口",
    )

    args = parser.parse_args()

    launch_app(
        share=args.share,
        server_name=args.host,
        server_port=args.port,
    )
