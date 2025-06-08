"""
ログ管理・エラー処理機能
抽出→プロンプト→API→出力 各ステップの詳細ログ保存
"""

import logging
import sys
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import traceback
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles


class LogLevel(Enum):
    """ログレベル"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ProcessStep(Enum):
    """処理ステップ"""
    EXTRACTION = "extraction"
    PROMPT_GENERATION = "prompt_generation"
    API_CALL = "api_call"
    ANALYSIS = "analysis"
    EXPORT = "export"
    COMPLETE = "complete"


@dataclass
class LogEntry:
    """ログエントリ"""
    timestamp: str
    level: str
    step: str
    url: str
    message: str
    details: Dict[str, Any] = None
    error_trace: Optional[str] = None
    processing_time: Optional[float] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class LPAnalyzerLogger:
    """LP Analyzer専用ロガー"""
    
    def __init__(self, 
                 log_dir: Path = Path("logs"),
                 log_level: LogLevel = LogLevel.INFO,
                 console_output: bool = True):
        
        self.log_dir = log_dir
        self.log_level = log_level
        self.console_output = console_output
        
        # ログディレクトリ作成
        self.log_dir.mkdir(exist_ok=True)
        
        # ログファイル名
        timestamp = datetime.now().strftime("%Y%m%d")
        self.main_log_file = self.log_dir / f"lp_analyzer_{timestamp}.log"
        self.error_log_file = self.log_dir / f"lp_analyzer_errors_{timestamp}.log"
        self.json_log_file = self.log_dir / f"lp_analyzer_{timestamp}.json"
        
        # Python標準ロガー設定
        self.logger = logging.getLogger("lp_analyzer")
        self.logger.setLevel(getattr(logging, log_level.value))
        
        # ハンドラー設定
        self._setup_handlers()
        
        # JSONログリスト
        self.json_logs = []
    
    def _setup_handlers(self):
        """ログハンドラー設定"""
        # ファイルハンドラー
        file_handler = logging.FileHandler(
            self.main_log_file, encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, self.log_level.value))
        
        # エラーファイルハンドラー
        error_handler = logging.FileHandler(
            self.error_log_file, encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # フォーマッター
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        
        # ハンドラー追加
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        
        # コンソール出力
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.log_level.value))
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def log(self, 
            level: LogLevel,
            step: ProcessStep,
            url: str,
            message: str,
            details: Dict[str, Any] = None,
            error: Exception = None,
            processing_time: float = None):
        """ログエントリ作成"""
        
        # ログエントリ作成
        log_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level.value,
            step=step.value,
            url=url,
            message=message,
            details=details or {},
            processing_time=processing_time
        )
        
        # エラー情報追加
        if error:
            log_entry.error_trace = traceback.format_exc()
            log_entry.details["error_type"] = type(error).__name__
            log_entry.details["error_message"] = str(error)
        
        # Python標準ロガーでログ出力
        log_method = getattr(self.logger, level.value.lower())
        log_message = f"[{step.value}] {url} - {message}"
        
        if details:
            log_message += f" | Details: {json.dumps(details, ensure_ascii=False)}"
        
        if error:
            log_method(log_message, exc_info=True)
        else:
            log_method(log_message)
        
        # JSONログに追加
        self.json_logs.append(log_entry)
    
    def info(self, step: ProcessStep, url: str, message: str, **kwargs):
        """情報ログ"""
        self.log(LogLevel.INFO, step, url, message, **kwargs)
    
    def warning(self, step: ProcessStep, url: str, message: str, **kwargs):
        """警告ログ"""
        self.log(LogLevel.WARNING, step, url, message, **kwargs)
    
    def error(self, step: ProcessStep, url: str, message: str, error: Exception = None, **kwargs):
        """エラーログ"""
        self.log(LogLevel.ERROR, step, url, message, error=error, **kwargs)
    
    def debug(self, step: ProcessStep, url: str, message: str, **kwargs):
        """デバッグログ"""
        self.log(LogLevel.DEBUG, step, url, message, **kwargs)
    
    async def save_json_logs(self):
        """JSONログをファイルに保存"""
        if not self.json_logs:
            return
        
        json_data = {
            "session_start": self.json_logs[0].timestamp if self.json_logs else datetime.now().isoformat(),
            "session_end": datetime.now().isoformat(),
            "total_entries": len(self.json_logs),
            "logs": [asdict(log) for log in self.json_logs]
        }
        
        async with aiofiles.open(self.json_log_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(json_data, indent=2, ensure_ascii=False))
    
    def get_error_summary(self) -> Dict[str, Any]:
        """エラーサマリを取得"""
        error_logs = [log for log in self.json_logs if log.level == "ERROR"]
        
        if not error_logs:
            return {"total_errors": 0, "error_types": {}, "failed_urls": []}
        
        error_types = {}
        failed_urls = []
        
        for log in error_logs:
            error_type = log.details.get("error_type", "Unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if log.url not in failed_urls:
                failed_urls.append(log.url)
        
        return {
            "total_errors": len(error_logs),
            "error_types": error_types,
            "failed_urls": failed_urls,
            "error_rate": len(failed_urls) / len(set(log.url for log in self.json_logs)) * 100 if self.json_logs else 0
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンスサマリを取得"""
        step_times = {}
        
        for log in self.json_logs:
            if log.processing_time:
                step = log.step
                if step not in step_times:
                    step_times[step] = []
                step_times[step].append(log.processing_time)
        
        summary = {}
        for step, times in step_times.items():
            summary[step] = {
                "count": len(times),
                "total_time": sum(times),
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times)
            }
        
        return summary


class ErrorHandler:
    """エラーハンドリング"""
    
    def __init__(self, logger: LPAnalyzerLogger):
        self.logger = logger
    
    async def handle_extraction_error(self, url: str, error: Exception) -> Dict[str, Any]:
        """抽出エラーハンドリング"""
        self.logger.error(
            ProcessStep.EXTRACTION,
            url,
            "Content extraction failed",
            error=error,
            details={"recoverable": self._is_recoverable_error(error)}
        )
        
        return {
            "success": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "retry_recommended": self._should_retry(error)
        }
    
    async def handle_api_error(self, url: str, error: Exception) -> Dict[str, Any]:
        """API呼び出しエラーハンドリング"""
        self.logger.error(
            ProcessStep.API_CALL,
            url,
            "API call failed",
            error=error,
            details={
                "recoverable": self._is_recoverable_error(error),
                "rate_limited": "rate" in str(error).lower()
            }
        )
        
        return {
            "success": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "retry_recommended": self._should_retry(error),
            "wait_time": self._get_retry_wait_time(error)
        }
    
    async def handle_analysis_error(self, url: str, error: Exception) -> Dict[str, Any]:
        """分析エラーハンドリング"""
        self.logger.error(
            ProcessStep.ANALYSIS,
            url,
            "Analysis failed",
            error=error,
            details={"recoverable": self._is_recoverable_error(error)}
        )
        
        return {
            "success": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "retry_recommended": False  # 分析エラーは通常リトライしない
        }
    
    async def handle_export_error(self, url: str, error: Exception) -> Dict[str, Any]:
        """エクスポートエラーハンドリング"""
        self.logger.error(
            ProcessStep.EXPORT,
            url,
            "Export failed",
            error=error,
            details={"recoverable": self._is_recoverable_error(error)}
        )
        
        return {
            "success": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "retry_recommended": self._should_retry(error)
        }
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """リカバリ可能なエラーかチェック"""
        recoverable_errors = [
            "TimeoutError",
            "ConnectionError",
            "RateLimitError",
            "APITimeoutError",
            "HTTPError"
        ]
        
        error_name = type(error).__name__
        return error_name in recoverable_errors
    
    def _should_retry(self, error: Exception) -> bool:
        """リトライすべきエラーかチェック"""
        retry_errors = [
            "TimeoutError",
            "ConnectionError", 
            "RateLimitError",
            "APITimeoutError"
        ]
        
        error_name = type(error).__name__
        error_message = str(error).lower()
        
        # エラー名でチェック
        if error_name in retry_errors:
            return True
        
        # エラーメッセージでチェック
        retry_keywords = ["timeout", "rate limit", "connection", "temporary"]
        return any(keyword in error_message for keyword in retry_keywords)
    
    def _get_retry_wait_time(self, error: Exception) -> int:
        """リトライ待機時間を取得"""
        error_message = str(error).lower()
        
        if "rate limit" in error_message:
            return 60  # レート制限の場合は60秒
        elif "timeout" in error_message:
            return 10  # タイムアウトの場合は10秒
        else:
            return 5   # その他は5秒


class ProgressTracker:
    """進捗トラッキング"""
    
    def __init__(self, logger: LPAnalyzerLogger):
        self.logger = logger
        self.start_time = None
        self.step_start_times = {}
    
    def start_session(self, total_urls: int):
        """セッション開始"""
        self.start_time = datetime.now()
        self.total_urls = total_urls
        
        self.logger.info(
            ProcessStep.COMPLETE,
            "session",
            f"Analysis session started",
            details={"total_urls": total_urls}
        )
    
    def start_step(self, step: ProcessStep, url: str):
        """ステップ開始"""
        self.step_start_times[f"{step.value}_{url}"] = datetime.now()
        
        self.logger.debug(
            step,
            url,
            f"Step {step.value} started"
        )
    
    def end_step(self, step: ProcessStep, url: str, success: bool = True, details: Dict[str, Any] = None):
        """ステップ終了"""
        step_key = f"{step.value}_{url}"
        
        if step_key in self.step_start_times:
            processing_time = (datetime.now() - self.step_start_times[step_key]).total_seconds()
            del self.step_start_times[step_key]
        else:
            processing_time = None
        
        status = "completed" if success else "failed"
        
        self.logger.info(
            step,
            url,
            f"Step {step.value} {status}",
            details=details,
            processing_time=processing_time
        )
    
    def end_session(self, processed_urls: int, successful_urls: int):
        """セッション終了"""
        if self.start_time:
            total_time = (datetime.now() - self.start_time).total_seconds()
        else:
            total_time = 0
        
        self.logger.info(
            ProcessStep.COMPLETE,
            "session",
            "Analysis session completed",
            details={
                "total_urls": self.total_urls,
                "processed_urls": processed_urls,
                "successful_urls": successful_urls,
                "success_rate": (successful_urls / processed_urls * 100) if processed_urls > 0 else 0,
                "total_processing_time": total_time
            },
            processing_time=total_time
        )