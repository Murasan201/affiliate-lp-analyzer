#!/usr/bin/env python3
"""
LP Analyzer - アフィリエイトLP自動分析ツール
メインCLIインターフェース
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional
import time

import click
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from src.core import JobQueue, JobProcessor, URLJob, JobStatus
from src.extractors import WebExtractor, ExtractedContent
from src.analyzers import LPAnalyzer, LPAnalysisResult
from src.exporters import MarkdownExporter
from src.utils import (
    OpenAIClient, 
    LPAnalyzerLogger, 
    ErrorHandler, 
    ProgressTracker,
    LogLevel,
    ProcessStep
)

# Rich console
console = Console()

# 環境変数ロード
load_dotenv()


class LPAnalyzerCLI:
    """LP Analyzer CLIクラス"""
    
    def __init__(self):
        self.console = console
        self.job_queue = JobQueue()
        self.logger = LPAnalyzerLogger(console_output=True)
        self.error_handler = ErrorHandler(self.logger)
        self.progress_tracker = ProgressTracker(self.logger)
        
        # OpenAI APIキーチェック
        if not os.getenv("OPENAI_API_KEY"):
            self.console.print("[red]Error: OPENAI_API_KEY not found in environment variables[/red]")
            self.console.print("Please set your OpenAI API key in .env file or environment variable")
            sys.exit(1)
    
    async def analyze_url(self, url: str) -> Optional[LPAnalysisResult]:
        """単一URL分析"""
        self.progress_tracker.start_step(ProcessStep.EXTRACTION, url)
        
        try:
            # コンテンツ抽出
            async with WebExtractor() as extractor:
                content = await extractor.extract_content(url)
            
            self.progress_tracker.end_step(ProcessStep.EXTRACTION, url, True)
            self.progress_tracker.start_step(ProcessStep.ANALYSIS, url)
            
            # OpenAIクライアント初期化
            openai_client = OpenAIClient()
            await openai_client.initialize()
            
            # LP分析
            analyzer = LPAnalyzer(openai_client)
            result = await analyzer.analyze_lp(content)
            
            self.progress_tracker.end_step(ProcessStep.ANALYSIS, url, True)
            
            return result, content
            
        except Exception as e:
            await self.error_handler.handle_extraction_error(url, e)
            return None, None
    
    async def process_job_queue(self, batch_mode: bool = False) -> dict:
        """ジョブキュー処理"""
        job_processor = JobProcessor(max_concurrent=3)
        
        async def processor_func(url: str):
            return await self.analyze_url(url)
        
        return await job_processor.process_jobs(
            self.job_queue, 
            processor_func, 
            batch_mode
        )


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='詳細ログ出力')
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']))
@click.pass_context
def cli(ctx, verbose, log_level):
    """LP Analyzer - アフィリエイトLP自動分析ツール"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['log_level'] = log_level


@cli.command()
@click.argument('url')
@click.option('--output', '-o', help='出力ファイル名（省略時は自動生成）')
@click.option('--format', '-f', 'output_format', default='markdown', 
              type=click.Choice(['markdown', 'json', 'both']))
@click.pass_context
async def analyze(ctx, url: str, output: Optional[str], output_format: str):
    """単一URLを分析"""
    
    analyzer_cli = LPAnalyzerCLI()
    
    console.print(f"[blue]Analyzing URL:[/blue] {url}")
    
    with console.status("[bold green]Extracting content...") as status:
        result, content = await analyzer_cli.analyze_url(url)
    
    if not result:
        console.print("[red]Analysis failed[/red]")
        return
    
    # レポート生成
    exporter = MarkdownExporter()
    
    console.print("[blue]Generating report...[/blue]")
    
    if output_format in ['markdown', 'both']:
        md_file = await exporter.export_individual_report(
            result, content, output if output and output.endswith('.md') else None
        )
        console.print(f"[green]Markdown report saved:[/green] {md_file}")
    
    if output_format in ['json', 'both']:
        json_file = await exporter.export_json_data([result])
        console.print(f"[green]JSON data saved:[/green] {json_file}")
    
    # サマリ表示
    _display_analysis_summary(result)


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--batch', '-b', is_flag=True, help='バッチ並列実行（デフォルトは順次実行）')
@click.option('--max-concurrent', '-c', default=3, help='最大並列実行数')
@click.option('--resume', '-r', is_flag=True, help='中断した処理を再開')
@click.pass_context
async def batch(ctx, csv_file: str, batch: bool, max_concurrent: int, resume: bool):
    """CSVファイルから一括分析"""
    
    analyzer_cli = LPAnalyzerCLI()
    csv_path = Path(csv_file)
    
    console.print(f"[blue]Loading URLs from:[/blue] {csv_path}")
    
    # 進捗復元またはCSVロード
    if resume:
        loaded = await analyzer_cli.job_queue.load_progress()
        if loaded:
            console.print("[green]Progress restored[/green]")
        else:
            console.print("[yellow]No previous progress found, starting fresh[/yellow]")
            await analyzer_cli.job_queue.load_urls_from_csv(csv_path)
    else:
        url_count = await analyzer_cli.job_queue.load_urls_from_csv(csv_path)
        console.print(f"[green]Loaded {url_count} URLs[/green]")
    
    # 進捗表示
    progress_summary = analyzer_cli.job_queue.get_progress_summary()
    _display_progress_table(progress_summary)
    
    # 処理実行
    console.print(f"[blue]Processing jobs ({'batch' if batch else 'sequential'} mode)...[/blue]")
    
    start_time = time.time()
    analyzer_cli.progress_tracker.start_session(progress_summary['total'])
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        
        task = progress.add_task("Processing URLs...", total=progress_summary['total'])
        
        # 結果収集用
        results = []
        contents = []
        
        # ジョブ処理
        pending_jobs = analyzer_cli.job_queue.get_pending_jobs()
        
        for job in pending_jobs:
            progress.update(task, description=f"Processing {job.url}")
            
            result, content = await analyzer_cli.analyze_url(job.url)
            
            if result and content:
                results.append(result)
                contents.append(content)
                await analyzer_cli.job_queue.update_job_status(job.url, JobStatus.COMPLETED)
            else:
                await analyzer_cli.job_queue.update_job_status(job.url, JobStatus.ERROR)
            
            progress.update(task, advance=1)
    
    # 処理完了
    end_time = time.time()
    processing_time = end_time - start_time
    
    analyzer_cli.progress_tracker.end_session(len(pending_jobs), len(results))
    
    # 統合レポート生成
    if results:
        console.print("[blue]Generating summary report...[/blue]")
        exporter = MarkdownExporter()
        
        summary_file = await exporter.export_summary_report(results, contents)
        console.print(f"[green]Summary report saved:[/green] {summary_file}")
        
        json_file = await exporter.export_json_data(results)
        console.print(f"[green]JSON data saved:[/green] {json_file}")
    
    # 最終サマリ
    final_summary = analyzer_cli.job_queue.get_progress_summary()
    _display_final_summary(final_summary, processing_time)
    
    # ログ保存
    await analyzer_cli.logger.save_json_logs()


@cli.command()
@click.pass_context
async def status(ctx):
    """現在の進捗状況を表示"""
    
    analyzer_cli = LPAnalyzerCLI()
    
    # 進捗読み込み
    loaded = await analyzer_cli.job_queue.load_progress()
    
    if not loaded:
        console.print("[yellow]No progress data found[/yellow]")
        return
    
    # 進捗表示
    progress_summary = analyzer_cli.job_queue.get_progress_summary()
    _display_progress_table(progress_summary)
    
    # エラーサマリ
    error_summary = analyzer_cli.logger.get_error_summary()
    if error_summary['total_errors'] > 0:
        _display_error_summary(error_summary)


@cli.command()
@click.option('--reset-errors', is_flag=True, help='エラー状態のジョブをリセット')
@click.pass_context
async def reset(ctx, reset_errors: bool):
    """ジョブ状態をリセット"""
    
    analyzer_cli = LPAnalyzerCLI()
    
    # 進捗読み込み
    loaded = await analyzer_cli.job_queue.load_progress()
    
    if not loaded:
        console.print("[yellow]No progress data found[/yellow]")
        return
    
    if reset_errors:
        error_jobs = analyzer_cli.job_queue.get_jobs_by_status(JobStatus.ERROR)
        
        for job in error_jobs:
            await analyzer_cli.job_queue.reset_job(job.url)
        
        console.print(f"[green]Reset {len(error_jobs)} error jobs[/green]")
    else:
        # 全ジョブリセット確認
        if click.confirm("Reset all jobs to pending status?"):
            for job in analyzer_cli.job_queue.jobs:
                await analyzer_cli.job_queue.reset_job(job.url)
            
            console.print("[green]All jobs reset to pending[/green]")


def _display_analysis_summary(result: LPAnalysisResult):
    """分析結果サマリ表示"""
    
    table = Table(title="Analysis Summary")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("URL", result.url)
    table.add_row("Processing Time", f"{result.processing_time:.2f}s")
    table.add_row("Cost", f"${result.total_cost:.4f}")
    table.add_row("Target Age", result.persona.age_range or "Unknown")
    table.add_row("Target Occupation", result.persona.occupation or "Unknown")
    table.add_row("Main USP", (result.usp.main_usp[:50] + "...") if result.usp.main_usp else "Not found")
    table.add_row("Techniques Used", ", ".join(result.copywriting.techniques_used))
    
    console.print(table)


def _display_progress_table(summary: dict):
    """進捗テーブル表示"""
    
    table = Table(title="Progress Summary")
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Percentage", style="yellow")
    
    total = summary['total']
    
    for status in ['pending', 'processing', 'completed', 'error', 'skipped']:
        count = summary.get(status, 0)
        percentage = (count / total * 100) if total > 0 else 0
        table.add_row(status.title(), str(count), f"{percentage:.1f}%")
    
    table.add_row("Total", str(total), "100.0%")
    
    console.print(table)


def _display_error_summary(error_summary: dict):
    """エラーサマリ表示"""
    
    panel = Panel(
        f"Total Errors: {error_summary['total_errors']}\n"
        f"Error Rate: {error_summary['error_rate']:.1f}%\n"
        f"Failed URLs: {len(error_summary['failed_urls'])}",
        title="Error Summary",
        border_style="red"
    )
    
    console.print(panel)


def _display_final_summary(summary: dict, processing_time: float):
    """最終サマリ表示"""
    
    panel = Panel(
        f"Total URLs: {summary['total']}\n"
        f"Completed: {summary.get('completed', 0)}\n"
        f"Failed: {summary.get('error', 0)}\n"
        f"Success Rate: {summary.get('progress', 0):.1f}%\n"
        f"Processing Time: {processing_time:.2f}s",
        title="Final Summary",
        border_style="green"
    )
    
    console.print(panel)


# 非同期コマンドのラッパー
def async_command(f):
    """非同期コマンドデコレータ"""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# 非同期コマンドをラップ
analyze = async_command(analyze)
batch = async_command(batch)
status = async_command(status)
reset = async_command(reset)


if __name__ == "__main__":
    cli()