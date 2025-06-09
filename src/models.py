from typing import Dict, Any, Callable, Awaitable, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

# 基本型
Config = Dict[str, Any]
ExecutorResult = Dict[str, Any]
ExecutorFunction = Callable[[Config], Awaitable[ExecutorResult]]

class SourceType(str, Enum):
    """データソースタイプ"""
    ACADEMIC = "academic"
    SOCIAL = "social"
    NEWS = "news"
    LLM = "llm"
    FORUM = "forum"

class UnifiedContent(BaseModel):
    """統一されたコンテンツ形式（詳細版）"""
    id: str
    title: str
    content: str
    source: str
    source_type: SourceType
    url: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    importance_score: Optional[float] = None

# Level 1: 統一出力フォーマット
class UnifiedItem(BaseModel):
    """統一されたアイテム形式（Level 1）"""
    id: str
    title: str
    summary: str
    url: str
    source: str
    source_type: SourceType
    published_at: datetime
    collected_at: datetime

class CollectionMetadata(BaseModel):
    """コレクションメタデータ"""
    collection_time: datetime
    total_sources: int
    total_items: int
    sources: List[str]

class UnifiedOutput(BaseModel):
    """最終的な統一出力フォーマット"""
    metadata: CollectionMetadata
    items: List[UnifiedItem]

class ExecutionResult(BaseModel):
    """実行結果"""
    executor_name: str
    success: bool
    data: Any
    start_time: datetime
    end_time: datetime
    execution_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutorConfig(BaseModel):
    """Executor設定"""
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = None  # cron形式
    dependencies: List[str] = Field(default_factory=list)
    timeout: Optional[int] = None
    retries: Optional[int] = None

class ExecutionConfig(BaseModel):
    """実行設定"""
    parallel: bool = True
    timeout: int = Field(default=300, gt=0)
    retries: int = Field(default=3, ge=0)
    output_dir: str = "./outputs"
    log_level: str = "INFO"
    save_results: bool = True

class WorkflowConfig(BaseModel):
    """ワークフロー設定"""
    executors: Dict[str, ExecutorConfig]
    execution: ExecutionConfig

class Pipeline(BaseModel):
    """実行パイプライン"""
    executors: List[ExecutorFunction]
    configs: List[Config]
    names: List[str]

    class Config:
        arbitrary_types_allowed = True

class HealthStatus(BaseModel):
    """健全性チェック結果"""
    status: str  # "healthy", "warning", "critical"
    message: str
    checks: Dict[str, bool]
    timestamp: datetime = Field(default_factory=datetime.now)
