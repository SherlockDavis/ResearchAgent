"""State Management 测试脚本"""
import asyncio
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.state import (
    ResearchState, PaperInfo, SubTask,
    create_initial_state, add_message, add_error,
    StateManager, StateValidator, get_state_summary
)
from datetime import datetime


def test_import():
    """测试模块导入"""
    print("=" * 60)
    print("测试0: 模块导入测试")
    print("=" * 60)

    try:
        from utils import StateManager, StateValidator, get_state_summary
        print("✓ 从utils导入StateManager成功")
        print("✓ 从utils导入StateValidator成功")
        print("✓ 从utils导入get_state_summary成功")
    except ImportError as e:
        print(f"✗ 从utils导入失败: {e}")
        return False

    try:
        from utils.state import StateManager, StateValidator, get_state_summary
        print("✓ 从utils.state导入成功")
    except ImportError as e:
        print(f"✗ 从utils.state导入失败: {e}")
        return False

    print("\n模块导入测试通过！\n")
    return True


def test_state_creation():
    """测试状态创建"""
    print("=" * 60)
    print("测试1: 状态创建测试")
    print("=" * 60)

    query = "测试研究问题"
    state = create_initial_state(query)

    assert state["query"] == query
    assert state["current_step"] == "init"
    assert state["papers"] == []
    assert state["paper_summaries"] == []
    assert state["analysis"] == {}
    assert state["report"] == ""
    assert state["messages"] == []
    assert state["errors"] == []
    assert isinstance(state["start_time"], datetime)
    assert state["end_time"] is None

    print("✓ 初始状态创建成功")
    print(f"  查询: {state['query']}")
    print(f"  初始步骤: {state['current_step']}")

    print("\n状态创建测试通过！\n")


def test_add_message_and_error():
    """测试添加消息和错误"""
    print("=" * 60)
    print("测试2: 消息和错误添加测试")
    print("=" * 60)

    state = create_initial_state("测试")

    # 添加消息
    add_message(state, "TestAgent", "测试消息")
    assert len(state["messages"]) == 1
    assert state["messages"][0]["agent"] == "TestAgent"
    assert state["messages"][0]["message"] == "测试消息"
    assert "timestamp" in state["messages"][0]
    print("✓ 添加消息成功")

    # 添加错误
    add_error(state, "测试错误")
    assert len(state["errors"]) == 1
    assert state["errors"][0]["error"] == "测试错误"
    assert "timestamp" in state["errors"][0]
    print("✓ 添加错误成功")

    print("\n消息和错误添加测试通过！\n")


def test_paper_info():
    """测试PaperInfo数据类"""
    print("=" * 60)
    print("测试3: PaperInfo数据类测试")
    print("=" * 60)

    paper = PaperInfo(
        title="Test Paper",
        authors=["Author A", "Author B"],
        abstract="This is a test abstract.",
        url="https://arxiv.org/abs/1234",
        arxiv_id="1234.56789",
        key_contributions=["Contribution 1"],
        methods=["Method 1"],
    )

    assert paper.title == "Test Paper"
    assert len(paper.authors) == 2
    assert paper.arxiv_id == "1234.56789"

    # 测试to_dict
    paper_dict = paper.to_dict()
    assert paper_dict["title"] == "Test Paper"
    assert paper_dict["arxiv_id"] == "1234.56789"
    print("✓ PaperInfo创建和转换成功")

    print("\nPaperInfo数据类测试通过！\n")


def test_subtask():
    """测试SubTask数据类"""
    print("=" * 60)
    print("测试4: SubTask数据类测试")
    print("=" * 60)

    task = SubTask(
        id="task_1",
        description="测试任务",
        agent_type="searcher",
        dependencies=[]
    )

    assert task.id == "task_1"
    assert task.status == "pending"
    assert task.agent_type == "searcher"

    # 测试to_dict
    task_dict = task.to_dict()
    assert task_dict["id"] == "task_1"
    assert task_dict["status"] == "pending"
    print("✓ SubTask创建和转换成功")

    print("\nSubTask数据类测试通过！\n")


def test_state_manager_save_load():
    """测试状态保存和加载"""
    print("=" * 60)
    print("测试5: 状态保存和加载测试")
    print("=" * 60)

    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(storage_dir=tmpdir)

        # 创建测试状态
        state = create_initial_state("测试查询")
        state["papers"] = [{"title": "Paper 1"}, {"title": "Paper 2"}]
        state["current_step"] = "search_completed"

        # 保存状态
        filepath = manager.save_state(state, session_id="test_session")
        assert Path(filepath).exists()
        print(f"✓ 状态保存成功: {filepath}")

        # 加载状态
        loaded_state = manager.load_state("test_session")
        assert loaded_state is not None
        assert loaded_state["query"] == "测试查询"
        assert loaded_state["current_step"] == "search_completed"
        assert len(loaded_state["papers"]) == 2
        print("✓ 状态加载成功")

        # 列出会话
        sessions = manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "test_session"
        print("✓ 会话列表获取成功")

        # 删除状态
        result = manager.delete_state("test_session")
        assert result is True
        assert not Path(filepath).exists()
        print("✓ 状态删除成功")

    print("\n状态保存和加载测试通过！\n")


def test_state_manager_snapshots():
    """测试状态快照"""
    print("=" * 60)
    print("测试6: 状态快照测试")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(storage_dir=tmpdir)

        # 创建测试状态
        state = create_initial_state("测试查询")
        state["current_step"] = "reading_completed"
        state["paper_summaries"] = [{"title": "Summary 1"}]

        # 创建快照
        snapshot_path = manager.create_snapshot(state, snapshot_name="after_reading")
        assert Path(snapshot_path).exists()
        print(f"✓ 快照创建成功: {snapshot_path}")

        # 列出快照
        snapshots = manager.list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["name"] == "after_reading"
        assert snapshots[0]["step"] == "reading_completed"
        print("✓ 快照列表获取成功")

        # 恢复快照
        restored_state = manager.restore_snapshot("after_reading")
        assert restored_state is not None
        assert restored_state["query"] == "测试查询"
        assert restored_state["current_step"] == "reading_completed"
        print("✓ 快照恢复成功")

    print("\n状态快照测试通过！\n")


def test_state_validator():
    """测试状态验证器"""
    print("=" * 60)
    print("测试7: 状态验证器测试")
    print("=" * 60)

    validator = StateValidator()

    # 测试有效状态
    valid_state = create_initial_state("有效查询")
    valid_state["papers"] = [{"title": "Paper 1"}]
    valid_state["paper_summaries"] = [{"title": "Summary 1"}]
    valid_state["current_step"] = "search_completed"

    errors = validator.validate_state(valid_state)
    assert len(errors) == 0
    print("✓ 有效状态验证通过")

    # 测试无效状态 - 缺少query
    invalid_state = create_initial_state("")
    invalid_state["query"] = ""
    errors = validator.validate_state(invalid_state)
    assert len(errors) > 0
    print(f"✓ 无效状态检测成功: {errors}")

    # 测试状态完成检查
    complete_state = create_initial_state("测试")
    complete_state["current_step"] = "report_completed"
    complete_state["report"] = "# Report"
    assert validator.is_state_complete(complete_state) is True
    print("✓ 完成状态检测成功")

    incomplete_state = create_initial_state("测试")
    incomplete_state["current_step"] = "search_completed"
    assert validator.is_state_complete(incomplete_state) is False
    print("✓ 未完成状态检测成功")

    # 测试进度获取
    progress = validator.get_state_progress(valid_state)
    assert "current_step" in progress
    assert "progress_percent" in progress
    assert "papers_found" in progress
    print(f"✓ 进度获取成功: {progress['progress_percent']}%")

    print("\n状态验证器测试通过！\n")


def test_get_state_summary():
    """测试状态摘要"""
    print("=" * 60)
    print("测试8: 状态摘要测试")
    print("=" * 60)

    state = create_initial_state("测试查询")
    state["papers"] = [{}, {}, {}]
    state["paper_summaries"] = [{}, {}]
    state["analysis"] = {"overview": "test"}
    state["report"] = "# Report"
    state["messages"] = [{"msg": "test"}]
    state["errors"] = []
    state["end_time"] = datetime.now()

    summary = get_state_summary(state)

    assert summary["query"] == "测试查询"
    assert summary["papers_count"] == 3
    assert summary["summaries_count"] == 2
    assert summary["has_analysis"] is True
    assert summary["has_report"] is True
    assert summary["message_count"] == 1
    assert summary["error_count"] == 0
    assert summary["duration_seconds"] is not None

    print("✓ 状态摘要生成成功")
    print(f"  摘要: {summary}")

    print("\n状态摘要测试通过！\n")


def test_state_serialization():
    """测试状态序列化"""
    print("=" * 60)
    print("测试9: 状态序列化测试")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(storage_dir=tmpdir)

        # 创建包含datetime的状态
        state = create_initial_state("测试")
        state["current_step"] = "report_completed"
        state["end_time"] = datetime.now()

        # 序列化
        state_dict = manager._serialize_state(state)
        assert isinstance(state_dict["start_time"], str)
        assert isinstance(state_dict["end_time"], str)
        print("✓ 序列化成功")

        # 反序列化
        restored_state = manager._deserialize_state(state_dict)
        assert isinstance(restored_state["start_time"], datetime)
        assert isinstance(restored_state["end_time"], datetime)
        print("✓ 反序列化成功")

    print("\n状态序列化测试通过！\n")


def test_state_transitions():
    """测试状态流转"""
    print("=" * 60)
    print("测试10: 状态流转测试")
    print("=" * 60)

    state = create_initial_state("测试")

    steps = [
        "init",
        "planning_completed",
        "search_completed",
        "reading_completed",
        "analysis_completed",
        "report_completed"
    ]

    for i, step in enumerate(steps):
        state["current_step"] = step
        progress = StateValidator.get_state_progress(state)
        expected_progress = (i / (len(steps) - 1)) * 100
        assert abs(progress["progress_percent"] - expected_progress) < 0.1
        print(f"✓ 步骤 '{step}' - 进度: {progress['progress_percent']:.1f}%")

    print("\n状态流转测试通过！\n")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("State Management 测试套件")
    print("=" * 60 + "\n")

    # 运行所有测试
    success = True

    success = test_import() and success
    test_state_creation()
    test_add_message_and_error()
    test_paper_info()
    test_subtask()
    test_state_manager_save_load()
    test_state_manager_snapshots()
    test_state_validator()
    test_get_state_summary()
    test_state_serialization()
    test_state_transitions()

    print("=" * 60)
    if success:
        print("所有测试通过！✓")
    else:
        print("部分测试失败 ✗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
