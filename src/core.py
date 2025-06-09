"""Core functional workflow engine"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback

from .models import ExecutorFunction, Config, ExecutionResult, Pipeline, ExecutorResult

logger = logging.getLogger(__name__)

# ==================== 純粋関数群 ====================

def create_result(
    executor_name: str,
    success: bool,
    data: Any = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    error: Optional[str] = None,
    **metadata
) -> ExecutionResult:
    """実行結果の生成"""
    start_time = start_time or datetime.now()
    end_time = end_time or datetime.now()
    execution_time = (end_time - start_time).total_seconds()

    return ExecutionResult(
        executor_name=executor_name,
        success=success,
        data=data,
        start_time=start_time,
        end_time=end_time,
        execution_time=execution_time,
        error=error,
        metadata=metadata
    )

def validate_config(config: Config, required_keys: List[str]) -> bool:
    """設定の検証"""
    return all(key in config for key in required_keys)

def filter_enabled_configs(configs: Dict[str, Dict]) -> Dict[str, Dict]:
    """有効な設定のみフィルタ"""
    return {
        name: config for name, config in configs.items()
        if config.get("enabled", True)
    }

def extract_output_count(data: Any) -> int:
    """出力件数の計算"""
    if isinstance(data, (list, dict)):
        return len(data)
    return 1 if data else 0

# ==================== 高階関数 ====================

def with_error_handling(executor: ExecutorFunction) -> ExecutorFunction:
    """エラーハンドリング付きExecutor"""
    async def wrapped(config: Config) -> ExecutorResult:
        executor_name = executor.__name__
        start_time = datetime.now()

        try:
            result = await executor(config)
            end_time = datetime.now()

            return {
                "executor_name": executor_name,
                "success": True,
                "data": result,
                "start_time": start_time,
                "end_time": end_time,
                "execution_time": (end_time - start_time).total_seconds(),
                "metadata": {"output_count": extract_output_count(result)}
            }

        except Exception as e:
            end_time = datetime.now()
            error_msg = str(e)
            error_details = traceback.format_exc()

            logger.error(f"Failed {executor_name}: {error_msg}")

            return {
                "executor_name": executor_name,
                "success": False,
                "data": None,
                "start_time": start_time,
                "end_time": end_time,
                "execution_time": (end_time - start_time).total_seconds(),
                "error": error_msg,
                "metadata": {"error_details": error_details}
            }

    return wrapped

# ==================== 実行エンジン ====================

async def run_single_executor(executor: ExecutorFunction, config: Config) -> ExecutionResult:
    """単一Executorの実行"""
    enhanced_executor = with_error_handling(executor)
    result = await enhanced_executor(config)
    return ExecutionResult(**result)

async def run_executors_parallel(executors: List[ExecutorFunction], configs: List[Config]) -> List[ExecutionResult]:
    """並列実行"""
    tasks = [run_single_executor(executor, config) for executor, config in zip(executors, configs)]
    return await asyncio.gather(*tasks)

async def run_executors_sequential(executors: List[ExecutorFunction], configs: List[Config]) -> List[ExecutionResult]:
    """逐次実行"""
    results = []
    for executor, config in zip(executors, configs):
        result = await run_single_executor(executor, config)
        results.append(result)

        status = "✓" if result.success else "✗"
        logger.info(f"{status} {result.executor_name}: {result.execution_time:.2f}s")

    return results

async def run_executors(
    executors: List[ExecutorFunction],
    configs: List[Config],
    parallel: bool = True,
    save_results: bool = True,
    output_dir: Path = Path("./outputs")
) -> List[ExecutionResult]:
    """Executor群の実行（メイン関数）"""

    logger.info(f"Starting {len(executors)} executors (parallel={parallel})")

    # 実行
    if parallel:
        results = await run_executors_parallel(executors, configs)
    else:
        results = await run_executors_sequential(executors, configs)

    # 統計
    successful = sum(1 for r in results if r.success)
    total_items = sum(r.metadata.get('output_count', 0) for r in results)

    logger.info(f"Completed: {successful}/{len(results)} successful, {total_items} total items")

    # 結果保存
    if save_results:
        await save_execution_results(results, output_dir)

    return results

# ==================== パイプライン ====================

def compose_pipeline(executor_configs: Dict[str, Dict], executor_registry: Dict[str, ExecutorFunction]) -> Pipeline:
    """設定からパイプラインを構築"""

    enabled_configs = filter_enabled_configs(executor_configs)

    executors = []
    configs = []
    names = []

    for name, config_data in enabled_configs.items():
        if name in executor_registry:
            executors.append(executor_registry[name])
            configs.append(config_data.get("config", {}))
            names.append(name)
        else:
            logger.warning(f"Unknown executor: {name}")

    return Pipeline(executors=executors, configs=configs, names=names)


# ==================== I/O ====================

async def save_execution_results(results: List[ExecutionResult], output_dir: Path):
    """実行結果の保存"""

    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = output_dir / f"execution_results_{timestamp}.json"

    # 結果をシリアライズ可能な形式に変換
    serializable_results = [
        {
            "executor_name": r.executor_name,
            "success": r.success,
            "data": r.data,
            "start_time": r.start_time.isoformat(),
            "end_time": r.end_time.isoformat(),
            "execution_time": r.execution_time,
            "error": r.error,
            "metadata": r.metadata
        }
        for r in results
    ]

    summary = {
        "execution_time": timestamp,
        "total_executors": len(results),
        "successful": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "total_items": sum(r.metadata.get('output_count', 0) for r in results),
        "results": serializable_results
    }

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info(f"Results saved to: {results_file}")

def load_config(config_path: Path) -> Dict[str, Any]:
    """YAML設定ファイルの読み込み"""
    import yaml
    print(config_path)

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
