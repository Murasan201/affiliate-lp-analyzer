"""
LP分析ワークフロー
ペルソナ仮説生成、USP・競合優位性抽出、ベネフィット分析、コピー手法タグ付け
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from ..extractors.web_extractor import ExtractedContent, ContentAnalyzer
from ..utils.openai_client import OpenAIClient, APIResponse


@dataclass
class PersonaAnalysis:
    """ペルソナ分析結果"""
    age_range: str = ""
    gender: str = ""
    occupation: str = ""
    income_level: str = ""
    lifestyle: str = ""
    values: str = ""
    problems: List[str] = None
    information_behavior: str = ""
    decision_factors: List[str] = None
    raw_analysis: str = ""
    
    def __post_init__(self):
        if self.problems is None:
            self.problems = []
        if self.decision_factors is None:
            self.decision_factors = []


@dataclass
class USPAnalysis:
    """USP分析結果"""
    main_usp: str = ""
    competitive_advantages: List[str] = None
    unique_value: str = ""
    evidence: List[str] = None
    key_features: List[str] = None
    raw_analysis: str = ""
    
    def __post_init__(self):
        if self.competitive_advantages is None:
            self.competitive_advantages = []
        if self.evidence is None:
            self.evidence = []
        if self.key_features is None:
            self.key_features = []


@dataclass
class BenefitAnalysis:
    """ベネフィット分析結果"""
    functional_benefits: List[str] = None
    emotional_benefits: List[str] = None
    key_keywords: List[str] = None
    power_words: List[str] = None
    urgency_elements: List[str] = None
    trust_elements: List[str] = None
    raw_analysis: str = ""
    
    def __post_init__(self):
        if self.functional_benefits is None:
            self.functional_benefits = []
        if self.emotional_benefits is None:
            self.emotional_benefits = []
        if self.key_keywords is None:
            self.key_keywords = []
        if self.power_words is None:
            self.power_words = []
        if self.urgency_elements is None:
            self.urgency_elements = []
        if self.trust_elements is None:
            self.trust_elements = []


@dataclass
class CopywritingAnalysis:
    """コピーライティング手法分析結果"""
    aida_elements: Dict[str, List[str]] = None
    pas_elements: Dict[str, List[str]] = None
    beaf_elements: Dict[str, List[str]] = None
    social_proof: List[str] = None
    authority: List[str] = None
    scarcity_urgency: List[str] = None
    storytelling: List[str] = None
    techniques_used: List[str] = None
    raw_analysis: str = ""
    
    def __post_init__(self):
        if self.aida_elements is None:
            self.aida_elements = {"attention": [], "interest": [], "desire": [], "action": []}
        if self.pas_elements is None:
            self.pas_elements = {"problem": [], "agitation": [], "solution": []}
        if self.beaf_elements is None:
            self.beaf_elements = {"benefit": [], "evidence": [], "advantage": [], "feature": []}
        if self.social_proof is None:
            self.social_proof = []
        if self.authority is None:
            self.authority = []
        if self.scarcity_urgency is None:
            self.scarcity_urgency = []
        if self.storytelling is None:
            self.storytelling = []
        if self.techniques_used is None:
            self.techniques_used = []


@dataclass
class LPAnalysisResult:
    """LP分析総合結果"""
    url: str
    timestamp: str
    persona: PersonaAnalysis
    usp: USPAnalysis
    benefits: BenefitAnalysis
    copywriting: CopywritingAnalysis
    content_quality: Dict[str, Any]
    keywords: List[str]
    analysis_summary: str = ""
    processing_time: float = 0.0
    total_cost: float = 0.0


class LPAnalyzer:
    """LP総合分析器"""
    
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
        self.content_analyzer = ContentAnalyzer()
    
    async def analyze_lp(self, content: ExtractedContent) -> LPAnalysisResult:
        """LP総合分析"""
        start_time = datetime.now()
        
        # 基本的なコンテンツ品質分析
        content_quality = self.content_analyzer.analyze_content_quality(content)
        keywords = self.content_analyzer.extract_keywords(content)
        
        # 分析用データ準備
        analysis_data = self._prepare_analysis_data(content)
        
        # 並列分析実行
        persona_task = asyncio.create_task(self._analyze_persona(analysis_data))
        usp_task = asyncio.create_task(self._analyze_usp(analysis_data))
        benefits_task = asyncio.create_task(self._analyze_benefits(analysis_data))
        copywriting_task = asyncio.create_task(self._analyze_copywriting(analysis_data))
        
        # 結果取得
        persona_response = await persona_task
        usp_response = await usp_task
        benefits_response = await benefits_task
        copywriting_response = await copywriting_task
        
        # 結果解析
        persona = self._parse_persona_analysis(persona_response.content)
        usp = self._parse_usp_analysis(usp_response.content)
        benefits = self._parse_benefit_analysis(benefits_response.content)
        copywriting = self._parse_copywriting_analysis(copywriting_response.content)
        
        # 総合サマリ生成
        summary = await self._generate_summary(content, persona, usp, benefits, copywriting)
        
        # 処理時間・コスト計算
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        total_cost = sum([
            persona_response.cost_estimate,
            usp_response.cost_estimate,
            benefits_response.cost_estimate,
            copywriting_response.cost_estimate
        ])
        
        return LPAnalysisResult(
            url=content.url,
            timestamp=start_time.isoformat(),
            persona=persona,
            usp=usp,
            benefits=benefits,
            copywriting=copywriting,
            content_quality=content_quality,
            keywords=keywords,
            analysis_summary=summary,
            processing_time=processing_time,
            total_cost=total_cost
        )
    
    def _prepare_analysis_data(self, content: ExtractedContent) -> Dict[str, Any]:
        """分析用データ準備"""
        # 見出しをテキスト化
        headings_text = ""
        for level, headings in content.headings.items():
            if headings:
                headings_text += f"{level.upper()}: " + ", ".join(headings) + "\n"
        
        # CTA要素をテキスト化
        cta_text = ""
        for cta in content.cta_elements:
            cta_text += f"[{cta.get('type', 'unknown')}] {cta.get('text', '')}\n"
        
        # フォーム要素をテキスト化
        form_text = ""
        for form in content.form_elements:
            form_text += f"Form: {form.get('action', '')} "
            for field in form.get('fields', []):
                form_text += f"{field.get('label', field.get('name', ''))} ({field.get('type', '')}), "
            form_text += "\n"
        
        return {
            "title": content.title,
            "meta_description": content.meta_description,
            "headings": headings_text.strip(),
            "main_text": content.main_text[:8000],  # 長すぎる場合は制限
            "cta_elements": cta_text.strip(),
            "form_elements": form_text.strip(),
            "url": content.url
        }
    
    async def _analyze_persona(self, data: Dict[str, Any]) -> APIResponse:
        """ペルソナ分析"""
        return await self.openai_client.analyze_with_template("persona_analysis", data)
    
    async def _analyze_usp(self, data: Dict[str, Any]) -> APIResponse:
        """USP分析"""
        return await self.openai_client.analyze_with_template("usp_analysis", data)
    
    async def _analyze_benefits(self, data: Dict[str, Any]) -> APIResponse:
        """ベネフィット分析"""
        return await self.openai_client.analyze_with_template("benefit_analysis", data)
    
    async def _analyze_copywriting(self, data: Dict[str, Any]) -> APIResponse:
        """コピーライティング手法分析"""
        return await self.openai_client.analyze_with_template("copywriting_analysis", data)
    
    def _parse_persona_analysis(self, analysis_text: str) -> PersonaAnalysis:
        """ペルソナ分析結果をパース"""
        persona = PersonaAnalysis(raw_analysis=analysis_text)
        
        # 簡易的なパースロジック（実際の実装では正規表現等を使用）
        lines = analysis_text.lower().split('\n')
        
        for line in lines:
            if '年齢' in line or 'age' in line:
                persona.age_range = self._extract_value_from_line(line)
            elif '性別' in line or 'gender' in line:
                persona.gender = self._extract_value_from_line(line)
            elif '職業' in line or 'occupation' in line:
                persona.occupation = self._extract_value_from_line(line)
            elif '収入' in line or 'income' in line:
                persona.income_level = self._extract_value_from_line(line)
            elif 'ライフスタイル' in line or 'lifestyle' in line:
                persona.lifestyle = self._extract_value_from_line(line)
        
        return persona
    
    def _parse_usp_analysis(self, analysis_text: str) -> USPAnalysis:
        """USP分析結果をパース"""
        usp = USPAnalysis(raw_analysis=analysis_text)
        
        # 主要USPを抽出（最初の段落を使用）
        paragraphs = analysis_text.split('\n\n')
        if paragraphs:
            usp.main_usp = paragraphs[0][:200]  # 200文字制限
        
        # 差別化ポイントを抽出
        usp.competitive_advantages = self._extract_list_items(analysis_text, ['差別化', '優位性', 'advantage'])
        usp.evidence = self._extract_list_items(analysis_text, ['証拠', '根拠', 'evidence'])
        usp.key_features = self._extract_list_items(analysis_text, ['特徴', 'feature'])
        
        return usp
    
    def _parse_benefit_analysis(self, analysis_text: str) -> BenefitAnalysis:
        """ベネフィット分析結果をパース"""
        benefits = BenefitAnalysis(raw_analysis=analysis_text)
        
        benefits.functional_benefits = self._extract_list_items(analysis_text, ['機能的', 'functional'])
        benefits.emotional_benefits = self._extract_list_items(analysis_text, ['感情的', 'emotional'])
        benefits.key_keywords = self._extract_list_items(analysis_text, ['キーワード', 'keyword'])
        benefits.power_words = self._extract_list_items(analysis_text, ['パワーワード', 'power word'])
        benefits.urgency_elements = self._extract_list_items(analysis_text, ['緊急性', 'urgency'])
        benefits.trust_elements = self._extract_list_items(analysis_text, ['信頼性', 'trust'])
        
        return benefits
    
    def _parse_copywriting_analysis(self, analysis_text: str) -> CopywritingAnalysis:
        """コピーライティング分析結果をパース"""
        copywriting = CopywritingAnalysis(raw_analysis=analysis_text)
        
        # 使用されている手法を検出
        techniques = []
        text_lower = analysis_text.lower()
        
        if 'aida' in text_lower:
            techniques.append('AIDA')
            copywriting.aida_elements = {
                "attention": self._extract_list_items(analysis_text, ['注意', 'attention']),
                "interest": self._extract_list_items(analysis_text, ['関心', 'interest']),
                "desire": self._extract_list_items(analysis_text, ['欲求', 'desire']),
                "action": self._extract_list_items(analysis_text, ['行動', 'action'])
            }
        
        if 'pas' in text_lower:
            techniques.append('PAS')
            copywriting.pas_elements = {
                "problem": self._extract_list_items(analysis_text, ['問題', 'problem']),
                "agitation": self._extract_list_items(analysis_text, ['共感', 'agitation']),
                "solution": self._extract_list_items(analysis_text, ['解決', 'solution'])
            }
        
        if 'beaf' in text_lower:
            techniques.append('BEAF')
        
        if '社会的証明' in text_lower or 'social proof' in text_lower:
            techniques.append('Social Proof')
            copywriting.social_proof = self._extract_list_items(analysis_text, ['社会的証明', 'social proof'])
        
        if '権威' in text_lower or 'authority' in text_lower:
            techniques.append('Authority')
            copywriting.authority = self._extract_list_items(analysis_text, ['権威', 'authority'])
        
        if '希少性' in text_lower or 'scarcity' in text_lower or '緊急性' in text_lower:
            techniques.append('Scarcity/Urgency')
            copywriting.scarcity_urgency = self._extract_list_items(analysis_text, ['希少性', 'scarcity', '緊急性', 'urgency'])
        
        copywriting.techniques_used = techniques
        
        return copywriting
    
    def _extract_value_from_line(self, line: str) -> str:
        """行から値を抽出"""
        # コロンや「：」の後の部分を取得
        for separator in [':', '：', '=']:
            if separator in line:
                parts = line.split(separator, 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return ""
    
    def _extract_list_items(self, text: str, keywords: List[str]) -> List[str]:
        """特定のキーワードに関連するリストアイテムを抽出"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in keywords):
                # リストマーカーを除去
                cleaned_line = line
                for marker in ['・', '•', '-', '*', '1.', '2.', '3.', '4.', '5.']:
                    cleaned_line = cleaned_line.replace(marker, '').strip()
                
                if cleaned_line and len(cleaned_line) > 3:
                    items.append(cleaned_line[:100])  # 100文字制限
        
        return items[:10]  # 最大10項目
    
    async def _generate_summary(self, content: ExtractedContent, 
                               persona: PersonaAnalysis,
                               usp: USPAnalysis,
                               benefits: BenefitAnalysis,
                               copywriting: CopywritingAnalysis) -> str:
        """総合サマリ生成"""
        
        summary_prompt = f"""以下のLP分析結果から、アフィリエイト記事作成に役立つ要点をまとめてください。

【ペルソナ分析】
{persona.raw_analysis[:500]}

【USP分析】
{usp.raw_analysis[:500]}

【ベネフィット分析】
{benefits.raw_analysis[:500]}

【コピーライティング手法】
{copywriting.raw_analysis[:500]}

アフィリエイト記事作成時の要点を3〜5つのポイントでまとめてください。"""
        
        try:
            response = await self.openai_client.custom_analysis(
                system_prompt="あなたはアフィリエイトマーケティングの専門家です。LP分析結果から記事作成のポイントをまとめてください。",
                user_prompt=summary_prompt,
                max_tokens=1000
            )
            return response.content
        except Exception as e:
            return f"サマリ生成エラー: {str(e)}"