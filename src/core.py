"""Core functional workflow engine"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback

from .models import ExecutorFunction, Config, ExecutionResult, Pipeline, ExecutorResult, WorkflowConfig, ExecutorConfig, ExecutionConfig

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

def compose_pipeline(executor_configs: Dict[str, ExecutorConfig], executor_registry: Dict[str, ExecutorFunction]) -> Pipeline:
    """設定からパイプラインを構築"""

    executors = []
    configs = []
    names = []

    for name, executor_config in executor_configs.items():
        if not executor_config.enabled:
            logger.info(f"Skipping disabled executor: {name}")
            continue

        if name in executor_registry:
            executors.append(executor_registry[name])
            configs.append(executor_config.config)
            names.append(name)
            logger.info(f"Added executor: {name}")
        else:
            logger.warning(f"Unknown executor: {name}")

    return Pipeline(executors=executors, configs=configs, names=names)


# ==================== I/O ====================

def _convert_datetime_to_str(obj: Any) -> Any:
    """再帰的にdatetimeオブジェクトを文字列に変換"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_datetime_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_datetime_to_str(item) for item in obj]
    return obj

async def save_execution_results(results: List[ExecutionResult], output_dir: Path):
    """実行結果の保存"""

    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = output_dir / f"execution_results_{timestamp}.json"

    # 結果をシリアライズ可能な形式に変換
    serializable_results = []
    for r in results:
        result_dict = {
            "executor_name": r.executor_name,
            "success": r.success,
            "data": r.data,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "end_time": r.end_time.isoformat() if r.end_time else None,
            "execution_time": r.execution_time,
            "error": r.error,
            "metadata": r.metadata
        }
        # データ内のdatetimeオブジェクトも変換
        result_dict = _convert_datetime_to_str(result_dict)
        serializable_results.append(result_dict)

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

def load_config(config_path: Path) -> WorkflowConfig:
    """YAML設定ファイルの読み込みとバリデーション"""
    import yaml
    import os

    logger.info(f"Loading config from: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)

    # 環境変数展開
    def expand_env_vars(data: Any) -> Any:
        if isinstance(data, dict):
            return {k: expand_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [expand_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith('${') and data.endswith('}'):
            env_var = data[2:-1]
            return os.getenv(env_var, data)
        return data

    expanded_config = expand_env_vars(raw_config)

    try:
        # Executorの設定を個別に変換
        executor_configs = {}
        for name, exec_data in expanded_config.get('executors', {}).items():
            executor_configs[name] = ExecutorConfig(**exec_data)

        # Execution設定を変換
        execution_config = ExecutionConfig(**expanded_config.get('execution', {}))

        # WorkflowConfigを作成
        return WorkflowConfig(
            executors=executor_configs,
            execution=execution_config
        )

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        logger.error(f"Config structure: {list(expanded_config.keys())}")
        raise ValueError(f"Invalid configuration: {e}") from e
