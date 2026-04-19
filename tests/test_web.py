"""Web界面测试脚本"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import():
    """测试模块导入"""
    print("=" * 60)
    print("测试0: 模块导入测试")
    print("=" * 60)

    try:
        from web import ResearchApp, create_ui, launch_app
        print("✓ 从web导入ResearchApp成功")
        print("✓ 从web导入create_ui成功")
        print("✓ 从web导入launch_app成功")
    except ImportError as e:
        print(f"✗ 从web导入失败: {e}")
        return False

    try:
        from web.app import ResearchApp, create_ui, launch_app
        print("✓ 从web.app导入成功")
    except ImportError as e:
        print(f"✗ 从web.app导入失败: {e}")
        return False

    print("\n模块导入测试通过！\n")
    return True


def test_research_app_initialization():
    """测试ResearchApp初始化"""
    print("=" * 60)
    print("测试1: ResearchApp初始化测试")
    print("=" * 60)

    from web.app import ResearchApp

    try:
        app = ResearchApp()
        assert app.workflow is None
        assert app.current_state is None
        print("✓ ResearchApp初始化成功")
        return True
    except Exception as e:
        print(f"✗ ResearchApp初始化失败: {e}")
        return False


def test_research_app_save_report():
    """测试报告保存功能"""
    print("=" * 60)
    print("测试2: 报告保存功能测试")
    print("=" * 60)

    import tempfile
    from web.app import ResearchApp

    with tempfile.TemporaryDirectory() as tmpdir:
        app = ResearchApp()

        # 测试空报告
        result = app.save_report("")
        assert "没有可保存的报告" in result
        print("✓ 空报告检测成功")

        # 测试有效报告
        test_report = "# Test Report\n\nThis is a test."
        result = app.save_report(test_report)
        assert "报告已保存到" in result
        print(f"✓ 报告保存成功: {result}")

    print("\n报告保存功能测试通过！\n")
    return True


def test_research_app_execution_info():
    """测试执行信息获取"""
    print("=" * 60)
    print("测试3: 执行信息获取测试")
    print("=" * 60)

    from web.app import ResearchApp
    from utils.state import create_initial_state

    app = ResearchApp()

    # 测试无状态
    info = app.get_execution_info()
    assert "暂无执行信息" in info
    print("✓ 无状态检测成功")

    # 测试有状态
    state = create_initial_state("测试查询")
    state["papers"] = [{}, {}, {}]
    state["paper_summaries"] = [{}, {}]
    state["analysis"] = {"overview": "test"}
    state["report"] = "# Report"
    app.current_state = state

    info = app.get_execution_info()
    assert "执行摘要" in info
    assert "测试查询" in info
    assert "检索论文数" in info
    print("✓ 执行信息获取成功")
    print(f"  信息预览: {info[:100]}...")

    print("\n执行信息获取测试通过！\n")
    return True


def test_create_ui():
    """测试UI创建"""
    print("=" * 60)
    print("测试4: UI创建测试")
    print("=" * 60)

    import os
    # 跳过需要API密钥的测试
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ 未配置API密钥，跳过UI初始化测试")
        print("✓ UI模块导入成功（跳过初始化）")
        return True

    try:
        from web.app import create_ui
        import gradio as gr

        # 创建UI（不启动）
        demo = create_ui()
        assert demo is not None
        assert isinstance(demo, gr.Blocks)
        print("✓ UI创建成功")

        return True
    except Exception as e:
        print(f"✗ UI创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_components():
    """测试UI组件定义"""
    print("=" * 60)
    print("测试5: UI组件测试")
    print("=" * 60)

    try:
        import gradio as gr

        # 测试基本组件创建
        textbox = gr.Textbox(label="测试")
        assert textbox is not None
        print("✓ Textbox组件创建成功")

        button = gr.Button("测试按钮")
        assert button is not None
        print("✓ Button组件创建成功")

        slider = gr.Slider(minimum=0, maximum=100)
        assert slider is not None
        print("✓ Slider组件创建成功")

        markdown = gr.Markdown("# 测试")
        assert markdown is not None
        print("✓ Markdown组件创建成功")

        print("\nUI组件测试通过！\n")
        return True
    except Exception as e:
        print(f"✗ UI组件测试失败: {e}")
        return False


def test_gradio_import():
    """测试Gradio导入"""
    print("=" * 60)
    print("测试6: Gradio导入测试")
    print("=" * 60)

    try:
        import gradio as gr
        print(f"✓ Gradio版本: {gr.__version__}")

        # 测试主题
        theme = gr.themes.Soft()
        assert theme is not None
        print("✓ Gradio主题创建成功")

        return True
    except ImportError as e:
        print(f"✗ Gradio导入失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Web界面测试套件")
    print("=" * 60 + "\n")

    # 运行所有测试
    success = True

    success = test_import() and success
    success = test_research_app_initialization() and success
    success = test_research_app_save_report() and success
    success = test_research_app_execution_info() and success
    success = test_gradio_import() and success
    success = test_ui_components() and success
    success = test_create_ui() and success

    print("=" * 60)
    if success:
        print("所有测试通过！✓")
        print("\n启动Web界面:")
        print("  python -m web.app")
        print("  或")
        print("  python web/app.py")
    else:
        print("部分测试失败 ✗")
    print("=" * 60)


if __name__ == "__main__":
    main()
