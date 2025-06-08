"""
URLリスト管理とジョブキュー機能
CSVファイルからURL一括インポート、進捗管理、並列実行制御
"""

import asyncio
import csv
import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime
import aiofiles


class JobStatus(Enum):
    """ジョブ状態"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class URLJob:
    """URL処理ジョブ"""
    url: str
    priority: str = "medium"
    category: str = ""
    status: JobStatus = JobStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class JobQueue:
    """URLジョブキューマネージャー"""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.input_dir = data_dir / "input"
        self.output_dir = data_dir / "output"
        self.temp_dir = data_dir / "temp"
        self.jobs: List[URLJob] = []
        self.progress_file = self.temp_dir / "job_progress.json"
        
        # ディレクトリ作成
        for dir_path in [self.input_dir, self.output_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def load_urls_from_csv(self, csv_file: Path) -> int:
        """CSVファイルからURLを一括インポート"""
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        
        try:
            df = pd.read_csv(csv_file)
            required_columns = ['url']
            
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"CSV must contain columns: {required_columns}")
            
            new_jobs = []
            for _, row in df.iterrows():
                job = URLJob(
                    url=row['url'],
                    priority=row.get('priority', 'medium'),
                    category=row.get('category', '')
                )
                new_jobs.append(job)
            
            self.jobs.extend(new_jobs)
            await self.save_progress()
            
            return len(new_jobs)
            
        except Exception as e:
            raise ValueError(f"Failed to load CSV: {e}")
    
    async def add_url(self, url: str, priority: str = "medium", category: str = "") -> URLJob:
        """単一URLを追加"""
        job = URLJob(url=url, priority=priority, category=category)
        self.jobs.append(job)
        await self.save_progress()
        return job
    
    def get_pending_jobs(self) -> List[URLJob]:
        """未処理ジョブを取得"""
        return [job for job in self.jobs if job.status == JobStatus.PENDING]
    
    def get_jobs_by_status(self, status: JobStatus) -> List[URLJob]:
        """指定状態のジョブを取得"""
        return [job for job in self.jobs if job.status == status]
    
    def get_job_by_url(self, url: str) -> Optional[URLJob]:
        """URLでジョブを検索"""
        for job in self.jobs:
            if job.url == url:
                return job
        return None
    
    async def update_job_status(self, url: str, status: JobStatus, 
                               error_message: Optional[str] = None):
        """ジョブ状態を更新"""
        job = self.get_job_by_url(url)
        if not job:
            return
        
        job.status = status
        
        if status == JobStatus.PROCESSING:
            job.started_at = datetime.now().isoformat()
        elif status in [JobStatus.COMPLETED, JobStatus.ERROR, JobStatus.SKIPPED]:
            job.completed_at = datetime.now().isoformat()
        
        if error_message:
            job.error_message = error_message
            if status == JobStatus.ERROR:
                job.retry_count += 1
        
        await self.save_progress()
    
    def should_retry(self, job: URLJob) -> bool:
        """リトライ可能かチェック"""
        return job.status == JobStatus.ERROR and job.retry_count < job.max_retries
    
    def get_retry_jobs(self) -> List[URLJob]:
        """リトライ対象ジョブを取得"""
        return [job for job in self.jobs if self.should_retry(job)]
    
    async def reset_job(self, url: str):
        """ジョブを未処理状態にリセット"""
        job = self.get_job_by_url(url)
        if job:
            job.status = JobStatus.PENDING
            job.started_at = None
            job.completed_at = None
            job.error_message = None
            await self.save_progress()
    
    async def skip_job(self, url: str):
        """ジョブをスキップ"""
        await self.update_job_status(url, JobStatus.SKIPPED)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """進捗サマリを取得"""
        total = len(self.jobs)
        if total == 0:
            return {"total": 0, "pending": 0, "processing": 0, 
                   "completed": 0, "error": 0, "skipped": 0, "progress": 0}
        
        status_counts = {}
        for status in JobStatus:
            status_counts[status.value] = len(self.get_jobs_by_status(status))
        
        completed_count = status_counts.get('completed', 0)
        progress = (completed_count / total) * 100 if total > 0 else 0
        
        return {
            "total": total,
            **status_counts,
            "progress": round(progress, 2)
        }
    
    async def save_progress(self):
        """進捗をファイルに保存"""
        progress_data = {
            "jobs": [asdict(job) for job in self.jobs],
            "summary": self.get_progress_summary(),
            "last_updated": datetime.now().isoformat()
        }
        
        async with aiofiles.open(self.progress_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(progress_data, indent=2, ensure_ascii=False))
    
    async def load_progress(self) -> bool:
        """保存された進捗を読み込み"""
        if not self.progress_file.exists():
            return False
        
        try:
            async with aiofiles.open(self.progress_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                progress_data = json.loads(content)
            
            self.jobs = []
            for job_data in progress_data.get("jobs", []):
                job_data["status"] = JobStatus(job_data["status"])
                job = URLJob(**job_data)
                self.jobs.append(job)
            
            return True
            
        except Exception as e:
            print(f"Failed to load progress: {e}")
            return False
    
    async def export_results_csv(self, output_file: Optional[Path] = None) -> Path:
        """結果をCSVにエクスポート"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"job_results_{timestamp}.csv"
        
        jobs_data = []
        for job in self.jobs:
            job_dict = asdict(job)
            job_dict["status"] = job.status.value
            jobs_data.append(job_dict)
        
        df = pd.DataFrame(jobs_data)
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        return output_file


class JobProcessor:
    """ジョブ並列処理管理"""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_jobs: Dict[str, asyncio.Task] = {}
    
    async def process_jobs(self, job_queue: JobQueue, 
                          processor_func, 
                          batch_mode: bool = False) -> Dict[str, Any]:
        """ジョブを並列処理"""
        pending_jobs = job_queue.get_pending_jobs()
        retry_jobs = job_queue.get_retry_jobs()
        all_jobs = pending_jobs + retry_jobs
        
        if not all_jobs:
            return {"message": "No jobs to process", "processed": 0}
        
        results = {"processed": 0, "completed": 0, "errors": 0}
        
        if batch_mode:
            # バッチ並列実行
            tasks = []
            for job in all_jobs:
                task = asyncio.create_task(
                    self._process_single_job(job, job_queue, processor_func)
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # 順次実行
            for job in all_jobs:
                await self._process_single_job(job, job_queue, processor_func)
        
        return job_queue.get_progress_summary()
    
    async def _process_single_job(self, job: URLJob, job_queue: JobQueue, 
                                 processor_func):
        """単一ジョブを処理"""
        async with self.semaphore:
            try:
                await job_queue.update_job_status(job.url, JobStatus.PROCESSING)
                
                # 実際の処理関数を呼び出し
                result = await processor_func(job.url)
                
                await job_queue.update_job_status(job.url, JobStatus.COMPLETED)
                return result
                
            except Exception as e:
                error_msg = str(e)
                await job_queue.update_job_status(
                    job.url, JobStatus.ERROR, error_msg
                )
                raise
    
    def pause_processing(self):
        """処理を一時停止"""
        for task in self.active_jobs.values():
            task.cancel()
    
    async def resume_processing(self, job_queue: JobQueue, processor_func):
        """処理を再開"""
        processing_jobs = job_queue.get_jobs_by_status(JobStatus.PROCESSING)
        for job in processing_jobs:
            await job_queue.reset_job(job.url)
        
        return await self.process_jobs(job_queue, processor_func)