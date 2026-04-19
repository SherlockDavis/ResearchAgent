"""日志工具"""
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from config import get_settings


def setup_logger(name: str = "research_agent", timestamp: str = None) -> logging.Logger:
    """设置日志记录器

    配置包括：
    1. 控制台输出（始终启用）
    2. 文件输出（可配置，默认启用，每次运行生成新文件）

    Args:
        name: 日志记录器名称
        timestamp: 时间戳字符串，用于日志文件名，格式为 YYYYMMDD_HHMMSS
                  如果为None，则使用当前时间生成
    """
    settings = get_settings()

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 格式化
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台handler（始终添加）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler（根据配置添加）
    if settings.LOG_TO_FILE:
        try:
            # 确保日志目录存在
            log_file_path = Path(settings.LOG_FILE_PATH)
            log_dir = log_file_path.parent
            log_dir.mkdir(parents=True, exist_ok=True)

            # 使用传入的时间戳或生成新的时间戳
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"research_agent_{timestamp}.log"
            dated_log_path = log_dir / log_filename

            # 创建文件handler（每次运行生成新文件）
            file_handler = logging.FileHandler(
                filename=dated_log_path,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # 记录日志文件位置
            logger.info(f"日志文件已配置: {dated_log_path}")
        except Exception as e:
            # 文件日志配置失败时，仅记录到控制台
            logger.warning(f"文件日志配置失败: {e}")

    return logger


# 全局logger实例（使用默认时间戳）
logger = setup_logger()
