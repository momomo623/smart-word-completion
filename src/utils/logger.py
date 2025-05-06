"""日志配置模块."""

import sys
from typing import Any, Dict, Optional

from loguru import logger

from src.config.settings import settings


def setup_logger() -> None:
    """配置日志系统.
    
    设置日志格式、级别和输出位置。
    """
    # 清除默认的日志配置
    logger.remove()
    
    # 添加控制台日志处理器
    logger.add(
        sys.stderr,
        format=settings.log.format,
        level=settings.log.level,
        colorize=True,
    )
    
    # 添加文件日志处理器(如果已配置)
    if settings.log.log_file:
        log_path = settings.output_dir / settings.log.log_file
        logger.add(
            log_path,
            format=settings.log.format,
            level=settings.log.level,
            rotation=settings.log.rotation,
            retention=settings.log.retention,
        )
    
    logger.info(f"日志系统已初始化，级别：{settings.log.level}")

# 注意：不在模块级别调用setup_logger()，避免重复初始化
# 初始化将在 src/__init__.py 中进行 