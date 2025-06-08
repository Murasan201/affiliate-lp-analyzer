"""
Markdownレポート生成・エクスポート機能
各URLごとのレポート生成と統合サマリレポート作成
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
from jinja2 import Environment, FileSystemLoader, Template
import aiofiles

from ..analyzers.lp_analyzer import LPAnalysisResult
from ..extractors.web_extractor import ExtractedContent


class MarkdownReportTemplate:
    """Markdownレポートテンプレート"""
    
    INDIVIDUAL_REPORT_TEMPLATE = """# LP分析レポート

## 基本情報
- **URL**: {url}
- **分析日時**: {timestamp}
- **処理時間**: {processing_time:.2f}秒
- **分析コスト**: ${total_cost:.4f}

## ページ概要
- **タイトル**: {title}
- **メタディスクリプション**: {meta_description}
- **文字数**: {word_count}語
- **CTA数**: {cta_count}個
- **フォーム数**: {form_count}個

## ペルソナ分析

### ターゲット顧客像
- **年齢層**: {persona_age_range}
- **性別**: {persona_gender}
- **職業**: {persona_occupation}
- **収入レベル**: {persona_income_level}
- **ライフスタイル**: {persona_lifestyle}

### 課題・悩み
{persona_problems}

### 購買決定要因
{persona_decision_factors}

### 詳細分析
{persona_raw_analysis}

## USP・競合優位性分析

### 主要USP
{usp_main}

### 競合優位性
{usp_advantages}

### 提供価値
{usp_unique_value}

### 根拠・証拠
{usp_evidence}

### 詳細分析
{usp_raw_analysis}

## ベネフィット分析

### 機能的ベネフィット
{functional_benefits}

### 感情的ベネフィット
{emotional_benefits}

### 訴求キーワード
{key_keywords}

### パワーワード
{power_words}

### 緊急性・希少性要素
{urgency_elements}

### 信頼性要素
{trust_elements}

### 詳細分析
{benefits_raw_analysis}

## コピーライティング手法分析

### 使用されている手法
{copywriting_techniques}

### AIDA要素
{aida_elements}

### PAS要素
{pas_elements}

### 社会的証明
{social_proof}

### 権威性の活用
{authority}

### 希少性・緊急性の演出
{scarcity_urgency}

### 詳細分析
{copywriting_raw_analysis}

## コンテンツ品質評価

### SEO要素
{seo_elements}

### 構造分析
{structure_analysis}

### LP特徴
{lp_indicators}

## アフィリエイト記事作成のポイント

{analysis_summary}

## 抽出キーワード

{keywords}

---
*このレポートは LP Analyzer により自動生成されました*
"""

    SUMMARY_REPORT_TEMPLATE = """# LP分析統合レポート

## 分析概要
- **分析日時**: {timestamp}
- **対象URL数**: {total_urls}
- **総処理時間**: {total_processing_time:.2f}秒
- **総分析コスト**: ${total_cost:.4f}

## 分析結果サマリ

### 成功・失敗統計
- **成功**: {success_count}件
- **失敗**: {error_count}件
- **成功率**: {success_rate:.1f}%

### 共通ペルソナ傾向

{common_personas}

### 共通USP傾向

{common_usps}

### 頻出キーワード

{common_keywords}

### 効果的なコピー手法

{common_techniques}

## 個別分析結果

{individual_summaries}

## 業界・カテゴリ別インサイト

{category_insights}

## アフィリエイト戦略提案

{strategy_recommendations}

---
*このレポートは LP Analyzer により自動生成されました*
"""


class MarkdownExporter:
    """Markdownエクスポーター"""
    
    def __init__(self, output_dir: Path = Path("data/output"), 
                 templates_dir: Path = Path("templates")):
        self.output_dir = output_dir
        self.templates_dir = templates_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Jinja2環境設定
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)) if templates_dir.exists() else None,
            autoescape=False
        )
    
    async def export_individual_report(self, 
                                     analysis_result: LPAnalysisResult,
                                     extracted_content: ExtractedContent,
                                     filename: Optional[str] = None) -> Path:
        """個別レポートをエクスポート"""
        
        if filename is None:
            # URLからファイル名生成
            url_safe = analysis_result.url.replace('https://', '').replace('http://', '')
            url_safe = ''.join(c if c.isalnum() or c in '.-_' else '_' for c in url_safe)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lp_analysis_{url_safe}_{timestamp}.md"
        
        # テンプレートデータ準備
        template_data = self._prepare_individual_template_data(
            analysis_result, extracted_content
        )
        
        # Markdownコンテンツ生成
        content = MarkdownReportTemplate.INDIVIDUAL_REPORT_TEMPLATE.format(**template_data)
        
        # ファイル保存
        output_path = self.output_dir / filename
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        return output_path
    
    async def export_summary_report(self, 
                                   analysis_results: List[LPAnalysisResult],
                                   extracted_contents: List[ExtractedContent],
                                   filename: Optional[str] = None) -> Path:
        """統合サマリレポートをエクスポート"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lp_analysis_summary_{timestamp}.md"
        
        # テンプレートデータ準備
        template_data = self._prepare_summary_template_data(
            analysis_results, extracted_contents
        )
        
        # Markdownコンテンツ生成
        content = MarkdownReportTemplate.SUMMARY_REPORT_TEMPLATE.format(**template_data)
        
        # ファイル保存
        output_path = self.output_dir / filename
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        return output_path
    
    def _prepare_individual_template_data(self, 
                                        analysis_result: LPAnalysisResult,
                                        extracted_content: ExtractedContent) -> Dict[str, Any]:
        """個別レポート用テンプレートデータ準備"""
        
        # 基本情報
        data = {
            'url': analysis_result.url,
            'timestamp': analysis_result.timestamp,
            'processing_time': analysis_result.processing_time,
            'total_cost': analysis_result.total_cost,
            'title': extracted_content.title,
            'meta_description': extracted_content.meta_description,
            'word_count': analysis_result.content_quality.get('word_count', 0),
            'cta_count': analysis_result.content_quality.get('cta_count', 0),
            'form_count': analysis_result.content_quality.get('form_count', 0),
        }
        
        # ペルソナ情報
        persona = analysis_result.persona
        data.update({
            'persona_age_range': persona.age_range or "不明",
            'persona_gender': persona.gender or "不明",
            'persona_occupation': persona.occupation or "不明",
            'persona_income_level': persona.income_level or "不明",
            'persona_lifestyle': persona.lifestyle or "不明",
            'persona_problems': self._format_list(persona.problems),
            'persona_decision_factors': self._format_list(persona.decision_factors),
            'persona_raw_analysis': persona.raw_analysis or "分析結果なし",
        })
        
        # USP情報
        usp = analysis_result.usp
        data.update({
            'usp_main': usp.main_usp or "特定なし",
            'usp_advantages': self._format_list(usp.competitive_advantages),
            'usp_unique_value': usp.unique_value or "特定なし",
            'usp_evidence': self._format_list(usp.evidence),
            'usp_raw_analysis': usp.raw_analysis or "分析結果なし",
        })
        
        # ベネフィット情報
        benefits = analysis_result.benefits
        data.update({
            'functional_benefits': self._format_list(benefits.functional_benefits),
            'emotional_benefits': self._format_list(benefits.emotional_benefits),
            'key_keywords': self._format_list(benefits.key_keywords),
            'power_words': self._format_list(benefits.power_words),
            'urgency_elements': self._format_list(benefits.urgency_elements),
            'trust_elements': self._format_list(benefits.trust_elements),
            'benefits_raw_analysis': benefits.raw_analysis or "分析結果なし",
        })
        
        # コピーライティング情報
        copywriting = analysis_result.copywriting
        data.update({
            'copywriting_techniques': self._format_list(copywriting.techniques_used),
            'aida_elements': self._format_dict_list(copywriting.aida_elements),
            'pas_elements': self._format_dict_list(copywriting.pas_elements),
            'social_proof': self._format_list(copywriting.social_proof),
            'authority': self._format_list(copywriting.authority),
            'scarcity_urgency': self._format_list(copywriting.scarcity_urgency),
            'copywriting_raw_analysis': copywriting.raw_analysis or "分析結果なし",
        })
        
        # コンテンツ品質情報
        content_quality = analysis_result.content_quality
        data.update({
            'seo_elements': self._format_dict(content_quality.get('seo_elements', {})),
            'structure_analysis': self._format_dict(content_quality.get('heading_structure', {})),
            'lp_indicators': self._format_dict(
                extracted_content.page_structure.get('lp_indicators', {})
            ),
        })
        
        # その他
        data.update({
            'analysis_summary': analysis_result.analysis_summary or "サマリなし",
            'keywords': self._format_list(analysis_result.keywords[:20]),  # 上位20語
        })
        
        return data
    
    def _prepare_summary_template_data(self, 
                                     analysis_results: List[LPAnalysisResult],
                                     extracted_contents: List[ExtractedContent]) -> Dict[str, Any]:
        """統合レポート用テンプレートデータ準備"""
        
        success_results = [r for r in analysis_results if r.analysis_summary]
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_urls': len(analysis_results),
            'success_count': len(success_results),
            'error_count': len(analysis_results) - len(success_results),
            'success_rate': (len(success_results) / len(analysis_results) * 100) if analysis_results else 0,
            'total_processing_time': sum(r.processing_time for r in analysis_results),
            'total_cost': sum(r.total_cost for r in analysis_results),
        }
        
        # 共通傾向分析
        data.update({
            'common_personas': self._analyze_common_personas(success_results),
            'common_usps': self._analyze_common_usps(success_results),
            'common_keywords': self._analyze_common_keywords(success_results),
            'common_techniques': self._analyze_common_techniques(success_results),
        })
        
        # 個別サマリ
        data['individual_summaries'] = self._create_individual_summaries(
            success_results, extracted_contents
        )
        
        # カテゴリ別インサイト
        data['category_insights'] = self._create_category_insights(success_results)
        
        # 戦略提案
        data['strategy_recommendations'] = self._create_strategy_recommendations(success_results)
        
        return data
    
    def _format_list(self, items: List[str]) -> str:
        """リストをMarkdown形式に変換"""
        if not items:
            return "- 該当なし"
        return '\n'.join(f"- {item}" for item in items[:10])  # 最大10項目
    
    def _format_dict(self, data: Dict[str, Any]) -> str:
        """辞書をMarkdown形式に変換"""
        if not data:
            return "- データなし"
        
        result = []
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                value = ', '.join(str(v) for v in value)
            result.append(f"- **{key}**: {value}")
        
        return '\n'.join(result)
    
    def _format_dict_list(self, data: Dict[str, List[str]]) -> str:
        """辞書のリストをMarkdown形式に変換"""
        if not data:
            return "- データなし"
        
        result = []
        for category, items in data.items():
            if items:
                result.append(f"### {category.upper()}")
                result.append(self._format_list(items))
                result.append("")
        
        return '\n'.join(result) if result else "- データなし"
    
    def _analyze_common_personas(self, results: List[LPAnalysisResult]) -> str:
        """共通ペルソナ傾向分析"""
        if not results:
            return "分析対象なし"
        
        # 年齢層、職業の頻度分析
        age_ranges = [r.persona.age_range for r in results if r.persona.age_range]
        occupations = [r.persona.occupation for r in results if r.persona.occupation]
        
        common_info = []
        if age_ranges:
            most_common_age = max(set(age_ranges), key=age_ranges.count)
            common_info.append(f"- **主要年齢層**: {most_common_age}")
        
        if occupations:
            most_common_occupation = max(set(occupations), key=occupations.count)
            common_info.append(f"- **主要職業**: {most_common_occupation}")
        
        return '\n'.join(common_info) if common_info else "共通傾向なし"
    
    def _analyze_common_usps(self, results: List[LPAnalysisResult]) -> str:
        """共通USP傾向分析"""
        if not results:
            return "分析対象なし"
        
        # USPから共通キーワード抽出
        all_usps = [r.usp.main_usp for r in results if r.usp.main_usp]
        
        if not all_usps:
            return "USP情報なし"
        
        # 簡易的なキーワード抽出
        common_words = []
        for usp in all_usps:
            words = usp.split()[:10]  # 最初の10語
            common_words.extend(words)
        
        # 頻出単語を特定
        word_counts = {}
        for word in common_words:
            if len(word) > 2:  # 3文字以上
                word_counts[word] = word_counts.get(word, 0) + 1
        
        if word_counts:
            top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            return '\n'.join(f"- {word} ({count}回)" for word, count in top_words)
        
        return "共通キーワードなし"
    
    def _analyze_common_keywords(self, results: List[LPAnalysisResult]) -> str:
        """共通キーワード分析"""
        if not results:
            return "分析対象なし"
        
        all_keywords = []
        for result in results:
            all_keywords.extend(result.keywords[:10])  # 各結果から上位10語
        
        if not all_keywords:
            return "キーワードなし"
        
        # 頻度計算
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # 上位キーワード
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return '\n'.join(f"- {keyword} ({count}回)" for keyword, count in top_keywords)
    
    def _analyze_common_techniques(self, results: List[LPAnalysisResult]) -> str:
        """共通コピー手法分析"""
        if not results:
            return "分析対象なし"
        
        all_techniques = []
        for result in results:
            all_techniques.extend(result.copywriting.techniques_used)
        
        if not all_techniques:
            return "手法情報なし"
        
        # 頻度計算
        technique_counts = {}
        for technique in all_techniques:
            technique_counts[technique] = technique_counts.get(technique, 0) + 1
        
        # 使用率順
        sorted_techniques = sorted(technique_counts.items(), key=lambda x: x[1], reverse=True)
        
        return '\n'.join(f"- {technique}: {count}件 ({count/len(results)*100:.1f}%)" 
                        for technique, count in sorted_techniques)
    
    def _create_individual_summaries(self, 
                                   results: List[LPAnalysisResult],
                                   contents: List[ExtractedContent]) -> str:
        """個別サマリ作成"""
        summaries = []
        
        for i, result in enumerate(results):
            content = contents[i] if i < len(contents) else None
            title = content.title if content else "タイトル不明"
            
            summary = f"""### {title}
- **URL**: {result.url}
- **処理時間**: {result.processing_time:.2f}秒
- **主要USP**: {result.usp.main_usp[:100] if result.usp.main_usp else '特定なし'}...
- **ターゲット**: {result.persona.age_range or '不明'} {result.persona.gender or ''} {result.persona.occupation or ''}
- **使用手法**: {', '.join(result.copywriting.techniques_used) if result.copywriting.techniques_used else 'なし'}

"""
            summaries.append(summary)
        
        return '\n'.join(summaries)
    
    def _create_category_insights(self, results: List[LPAnalysisResult]) -> str:
        """カテゴリ別インサイト作成"""
        # 簡易実装（実際にはより高度な分析が可能）
        insights = []
        
        # コンバージョン要素の分析
        high_cta_count = sum(1 for r in results 
                           if r.content_quality.get('cta_count', 0) > 3)
        
        insights.append(f"- CTA要素が多い（4個以上）LP: {high_cta_count}件")
        
        # フォーム使用率
        form_usage = sum(1 for r in results 
                        if r.content_quality.get('form_count', 0) > 0)
        
        insights.append(f"- フォーム設置率: {form_usage/len(results)*100:.1f}%")
        
        return '\n'.join(insights) if insights else "インサイトなし"
    
    def _create_strategy_recommendations(self, results: List[LPAnalysisResult]) -> str:
        """戦略提案作成"""
        recommendations = []
        
        # 共通的な提案
        recommendations.append("### アフィリエイト記事戦略")
        recommendations.append("- ターゲットペルソナに響く感情的ベネフィットを強調")
        recommendations.append("- 競合優位性を明確に伝える比較コンテンツの作成")
        recommendations.append("- 社会的証明（口コミ・評判）コンテンツの活用")
        recommendations.append("- 緊急性・希少性を適切に演出")
        
        # データに基づく提案
        if results:
            avg_techniques = sum(len(r.copywriting.techniques_used) for r in results) / len(results)
            if avg_techniques > 2:
                recommendations.append("- 複数のコピー手法を組み合わせた構成が効果的")
        
        return '\n'.join(recommendations)
    
    async def export_json_data(self, 
                             analysis_results: List[LPAnalysisResult],
                             filename: Optional[str] = None) -> Path:
        """分析結果をJSON形式でエクスポート"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lp_analysis_data_{timestamp}.json"
        
        # JSON用データ変換
        json_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_count': len(analysis_results),
            'results': []
        }
        
        for result in analysis_results:
            result_dict = {
                'url': result.url,
                'timestamp': result.timestamp,
                'persona': {
                    'age_range': result.persona.age_range,
                    'gender': result.persona.gender,
                    'occupation': result.persona.occupation,
                    'income_level': result.persona.income_level,
                    'lifestyle': result.persona.lifestyle,
                    'problems': result.persona.problems,
                    'decision_factors': result.persona.decision_factors
                },
                'usp': {
                    'main_usp': result.usp.main_usp,
                    'competitive_advantages': result.usp.competitive_advantages,
                    'unique_value': result.usp.unique_value,
                    'evidence': result.usp.evidence
                },
                'benefits': {
                    'functional_benefits': result.benefits.functional_benefits,
                    'emotional_benefits': result.benefits.emotional_benefits,
                    'key_keywords': result.benefits.key_keywords,
                    'power_words': result.benefits.power_words
                },
                'copywriting': {
                    'techniques_used': result.copywriting.techniques_used,
                    'social_proof': result.copywriting.social_proof,
                    'authority': result.copywriting.authority
                },
                'content_quality': result.content_quality,
                'keywords': result.keywords,
                'processing_time': result.processing_time,
                'total_cost': result.total_cost
            }
            json_data['results'].append(result_dict)
        
        # ファイル保存
        output_path = self.output_dir / filename
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(json_data, indent=2, ensure_ascii=False))
        
        return output_path