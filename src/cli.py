import asyncio
import logging
from pathlib import Path
from typing import Dict

import click
from rich.console import Console
from rich.logging import RichHandler

from .core import run_executors, compose_pipeline, load_config
from .executors.arxiv import arxiv_fetcher
from .executors.chatGPT import chatgpt_fetcher
from .executors.genspark import genspark_fetcher
from .executors.twitter import twitter_fetcher
from .executors.reddit import reddit_fetcher
from .models import ExecutorFunction

AVAILABLE_EXECUTORS: Dict[str, ExecutorFunction] = {
    "arxiv": arxiv_fetcher,
    "chatgpt": chatgpt_fetcher,
    "genspark": genspark_fetcher,
    "twitter": twitter_fetcher,
    "reddit": reddit_fetcher,
}

console = Console()

def setup_logging(level: str):
    """ログ設定"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console)]
    )

@click.group()
@click.version_option()
def main():
    """Research Workflow - Functional data collection system"""
    pass

@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config/default.yml"),
    help="Configuration file path"
)
@click.option(
    "--executors",
    "-e",
    multiple=True,
    help="Specific executors to run"
)
@click.option(
    "--parallel/--sequential",
    default=True,
    help="Execution mode"
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("./outputs"),
    help="Output directory"
)
def run(config: Path, executors: tuple, parallel: bool, output_dir: Path):
    """Run the research workflow"""

    async def _run():
        # 設定読み込み
        workflow_config = load_config(config)
        setup_logging(workflow_config.get("execution", {}).get("log_level", "INFO"))

        # パイプライン構築
        if executors:
            # 指定されたExecutorのみ
            executor_configs = {
                name: workflow_config["executors"][name]
                for name in executors
                if name in workflow_config["executors"]
            }
        else:
            # 全Executor
            executor_configs = workflow_config["executors"]

        pipeline = compose_pipeline(executor_configs, AVAILABLE_EXECUTORS)

        if not pipeline.executors:
            console.print("[red]No executors to run[/red]")
            return

        console.print(f"[green]Running executors:[/green] {', '.join(pipeline.names)}")

        # 実行
        results = await run_executors(
            pipeline.executors,
            pipeline.configs,
            parallel=parallel,
            output_dir=output_dir
        )

        # サマリー
        successful = sum(1 for r in results if r.success)
        total_items = sum(r.metadata.get('output_count', 0) for r in results)

        console.print(f"\n[green]Completed:[/green] {successful}/{len(results)} executors, {total_items} total items")

    asyncio.run(_run())

@main.command()
def list():
    """List available executors"""
    console.print("[green]Available Executors:[/green]")
    for name in AVAILABLE_EXECUTORS.keys():
        console.print(f"  • {name}")

@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("config/default.yml"),
    help="Output config file path"
)
def init(output: Path):
    pass

if __name__ == "__main__":
    main()
