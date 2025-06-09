from typing import Dict, Any, Callable, Awaitable, List, NamedTuple, Optional
from datetime import datetime

# 基本型
Config = Dict[str, Any]
ExecutorResult = Dict[str, Any]
ExecutorFunction = Callable[[Config], Awaitable[ExecutorResult]]

class ExecutionResult(NamedTuple):
    """実行結果"""
    executor_name: str
    success: bool
    data: Any
    start_time: datetime
    end_time: datetime
    execution_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class Pipeline(NamedTuple):
    """実行パイプライン"""
    executors: List[ExecutorFunction]
    configs: List[Config]
    names: List[str]
