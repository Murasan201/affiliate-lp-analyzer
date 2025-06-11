"""
OpenAI API連携機能
プロンプト管理、レート制御、チャンク分割、リトライ処理
"""

import asyncio
import os
import json
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import openai
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import aiofiles
from asyncio_throttle import Throttler


@dataclass
class PromptTemplate:
    """プロンプトテンプレート"""
    name: str
    system_prompt: str
    user_prompt_template: str
    description: str = ""
    model: str = "o4-mini"
    max_completion_tokens: int = 4000


@dataclass
class APIResponse:
    """API応答データ"""
    content: str
    model: str
    tokens_used: int
    cost_estimate: float
    response_time: float
    timestamp: str


class TextChunker:
    """テキストチャンク分割"""
    
    def __init__(self, max_tokens: int = 12000, overlap_tokens: int = 200):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
    
    def estimate_tokens(self, text: str) -> int:
        """トークン数を推定（簡易版）"""
        # 日本語混在の場合の簡易推定: 文字数 * 0.75
        return int(len(text) * 0.75)
    
    def split_text(self, text: str) -> List[str]:
        """テキストをチャンクに分割"""
        if self.estimate_tokens(text) <= self.max_tokens:
            return [text]
        
        chunks = []
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    
                    # オーバーラップ処理
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + sentence
                    current_tokens = self.estimate_tokens(current_chunk)
                else:
                    # 単一文が最大トークンを超える場合
                    current_chunk = sentence
                    current_tokens = sentence_tokens
            else:
                current_chunk += sentence
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """文章を文に分割"""
        import re
        
        # 日本語の句読点と英語のピリオドで分割
        sentence_endings = r'[。！？\.\!\?]'
        sentences = re.split(f'({sentence_endings})', text)
        
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if sentence.strip():
                result.append(sentence + ' ')
        
        return result
    
    def _get_overlap_text(self, text: str) -> str:
        """オーバーラップテキストを取得"""
        sentences = self._split_into_sentences(text)
        
        overlap_text = ""
        overlap_tokens = 0
        
        # 末尾から遡ってオーバーラップ分を取得
        for sentence in reversed(sentences):
            sentence_tokens = self.estimate_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.overlap_tokens:
                overlap_text = sentence + overlap_text
                overlap_tokens += sentence_tokens
            else:
                break
        
        return overlap_text


class RateLimiter:
    """レート制限管理"""
    
    def __init__(self, requests_per_minute: int = 60, 
                 tokens_per_minute: int = 200000):
        self.requests_throttler = Throttler(rate_limit=requests_per_minute, period=60)
        self.tokens_per_minute = tokens_per_minute
        self.token_usage_history = []
    
    async def acquire_request_slot(self):
        """リクエスト枠を取得"""
        async with self.requests_throttler:
            pass
    
    async def check_token_limit(self, estimated_tokens: int):
        """トークン制限をチェック"""
        current_time = time.time()
        
        # 1分以内のトークン使用量を計算
        minute_ago = current_time - 60
        recent_usage = sum(
            usage['tokens'] for usage in self.token_usage_history
            if usage['timestamp'] > minute_ago
        )
        
        if recent_usage + estimated_tokens > self.tokens_per_minute:
            # 待機時間計算
            wait_time = 60 - (current_time - min(
                usage['timestamp'] for usage in self.token_usage_history
                if usage['timestamp'] > minute_ago
            ))
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    def record_token_usage(self, tokens: int):
        """トークン使用量を記録"""
        self.token_usage_history.append({
            'tokens': tokens,
            'timestamp': time.time()
        })
        
        # 古い履歴を削除
        minute_ago = time.time() - 60
        self.token_usage_history = [
            usage for usage in self.token_usage_history
            if usage['timestamp'] > minute_ago
        ]


class PromptManager:
    """プロンプト管理"""
    
    def __init__(self, templates_dir: Path = Path("templates")):
        self.templates_dir = templates_dir
        self.templates: Dict[str, PromptTemplate] = {}
        self.templates_dir.mkdir(exist_ok=True)
    
    async def load_templates(self):
        """テンプレートをロード"""
        await self._create_default_templates()
        
        for template_file in self.templates_dir.glob("*.json"):
            try:
                async with aiofiles.open(template_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    template_data = json.loads(content)
                    template = PromptTemplate(**template_data)
                    self.templates[template.name] = template
            except Exception as e:
                print(f"Failed to load template {template_file}: {e}")
    
    async def _create_default_templates(self):
        """デフォルトテンプレートを作成"""
        default_templates = [
            {
                "name": "persona_analysis",
                "description": "ペルソナ仮説生成",
                "system_prompt": "あなたはマーケティングの専門家です。提供されたランディングページの内容から、ターゲット顧客のペルソナを分析してください。",
                "user_prompt_template": """以下のランディングページの内容を分析し、想定されるターゲット顧客のペルソナを詳細に分析してください。

【ページ内容】
タイトル: {title}
メタディスクリプション: {meta_description}
見出し: {headings}
本文: {main_text}

以下の観点でペルソナを分析してください：
1. 年齢層・性別
2. 職業・収入レベル
3. ライフスタイル・価値観
4. 抱えている課題・悩み
5. 情報収集行動
6. 購買決定要因

分析結果は具体的で実用的な内容で回答してください。""",
                "model": "o4-mini",
                "max_completion_tokens": 4000
            },
            {
                "name": "usp_analysis",
                "description": "USP・競合優位性抽出",
                "system_prompt": "あなたはマーケティング戦略の専門家です。ランディングページからUSP（独自の強み）と競合優位性を抽出してください。",
                "user_prompt_template": """以下のランディングページの内容からUSP（Unique Selling Proposition）と競合優位性を分析してください。

【ページ内容】
タイトル: {title}
メタディスクリプション: {meta_description}
見出し: {headings}
本文: {main_text}
CTA要素: {cta_elements}

以下の観点で分析してください：
1. 主要なUSP・独自の強み
2. 競合他社との差別化ポイント
3. 顧客に提供する独自の価値
4. 証拠・根拠となる要素
5. 強みを支える具体的な特徴

実用的で説得力のある分析結果を提供してください。""",
                "model": "o4-mini",
                "max_completion_tokens": 4000
            },
            {
                "name": "benefit_analysis",
                "description": "ベネフィット・訴求キーワード抽出",
                "system_prompt": "あなたはコピーライティングの専門家です。ランディングページからベネフィットと訴求キーワードを抽出してください。",
                "user_prompt_template": """以下のランディングページの内容からベネフィットと効果的な訴求キーワードを抽出してください。

【ページ内容】
タイトル: {title}
メタディスクリプション: {meta_description}
見出し: {headings}
本文: {main_text}

以下の観点で分析してください：
1. 顧客が得られる具体的なベネフィット
2. 感情的ベネフィット vs 機能的ベネフィット
3. 効果的な訴求キーワード
4. パワーワード・感情を動かす表現
5. 緊急性・希少性を示す要素
6. 信頼性を高める要素

アフィリエイト記事作成に活用できる実用的な分析結果を提供してください。""",
                "model": "o4-mini",
                "max_completion_tokens": 4000
            },
            {
                "name": "copywriting_analysis",
                "description": "コピーライティング手法分析",
                "system_prompt": "あなたはコピーライティングの専門家です。ランディングページで使用されているコピーライティング手法を分析してください。",
                "user_prompt_template": """以下のランディングページの内容で使用されているコピーライティング手法を分析してください。

【ページ内容】
タイトル: {title}
メタディスクリプション: {meta_description}
見出し: {headings}
本文: {main_text}
CTA要素: {cta_elements}

以下の手法が使用されているかを分析してください：
1. AIDA（注意→関心→欲求→行動）
2. PAS（問題→共感→解決策）
3. BEAF（Benefit→Evidence→Advantage→Feature）
4. 社会的証明（口コミ、推薦など）
5. 権威性の活用
6. 希少性・緊急性の演出
7. ストーリーテリング

具体的にどの部分でどの手法が使われているかを詳しく分析してください。""",
                "model": "o4-mini",
                "max_completion_tokens": 4000
            }
        ]
        
        for template_data in default_templates:
            template_file = self.templates_dir / f"{template_data['name']}.json"
            if not template_file.exists():
                async with aiofiles.open(template_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(template_data, indent=2, ensure_ascii=False))
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """テンプレートを取得"""
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """テンプレート一覧を取得"""
        return list(self.templates.keys())


class OpenAIClient:
    """OpenAI APIクライアント"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 requests_per_minute: int = 60,
                 tokens_per_minute: int = 200000,
                 default_model: str = "o4-mini"):
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.rate_limiter = RateLimiter(requests_per_minute, tokens_per_minute)
        self.text_chunker = TextChunker()
        self.prompt_manager = PromptManager()
        self.default_model = default_model
        
        # コスト計算用の価格表（2024年6月時点）
        self.pricing = {
            "o4-mini": {"input": 0.00015, "output": 0.0006}  # per 1K tokens
        }
    
    async def initialize(self):
        """初期化"""
        await self.prompt_manager.load_templates()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
    )
    async def _make_api_call(self, messages: List[Dict[str, str]], 
                           model: str, 
                           max_completion_tokens: int) -> APIResponse:
        """API呼び出し（リトライ付き）"""
        
        # レート制限チェック
        await self.rate_limiter.acquire_request_slot()
        
        # トークン数推定
        estimated_tokens = sum(
            self.text_chunker.estimate_tokens(msg["content"]) 
            for msg in messages
        )
        await self.rate_limiter.check_token_limit(estimated_tokens)
        
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_completion_tokens
            )
            
            response_time = time.time() - start_time
            
            # トークン使用量記録
            tokens_used = response.usage.total_tokens
            self.rate_limiter.record_token_usage(tokens_used)
            
            # コスト計算
            cost_estimate = self._calculate_cost(
                model, 
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
            
            return APIResponse(
                content=response.choices[0].message.content,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
                response_time=response_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"API call failed: {e}")
            raise
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """コスト計算"""
        if model not in self.pricing:
            return 0.0
        
        prices = self.pricing[model]
        input_cost = (input_tokens / 1000) * prices["input"]
        output_cost = (output_tokens / 1000) * prices["output"]
        
        return input_cost + output_cost
    
    async def analyze_with_template(self, 
                                  template_name: str,
                                  content_data: Dict[str, Any]) -> APIResponse:
        """テンプレートを使用して分析"""
        
        template = self.prompt_manager.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # プロンプト生成
        user_prompt = template.user_prompt_template.format(**content_data)
        
        messages = [
            {"role": "system", "content": template.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._make_api_call(
            messages=messages,
            model=template.model,
            max_completion_tokens=template.max_completion_tokens
        )
    
    async def analyze_with_chunking(self, 
                                  template_name: str,
                                  large_content: str,
                                  additional_data: Dict[str, Any] = None) -> List[APIResponse]:
        """大きなコンテンツをチャンク分割して分析"""
        
        chunks = self.text_chunker.split_text(large_content)
        responses = []
        
        for i, chunk in enumerate(chunks):
            content_data = {"main_text": chunk}
            if additional_data:
                content_data.update(additional_data)
            
            # チャンク情報追加
            content_data["chunk_info"] = f"チャンク {i+1}/{len(chunks)}"
            
            response = await self.analyze_with_template(template_name, content_data)
            responses.append(response)
        
        return responses
    
    async def custom_analysis(self, 
                            system_prompt: str,
                            user_prompt: str,
                            model: Optional[str] = None,
                            max_completion_tokens: int = 4000) -> APIResponse:
        """カスタム分析"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._make_api_call(
            messages=messages,
            model=model or self.default_model,
            max_completion_tokens=max_completion_tokens
        )