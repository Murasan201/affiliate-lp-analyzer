"""
Web content extraction using Playwright
ヘッドレスブラウザによる最終レンダリングHTML取得とコンテンツ抽出
"""

import asyncio
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse


@dataclass
class ExtractedContent:
    """抽出されたコンテンツ"""
    url: str
    title: str = ""
    meta_description: str = ""
    headings: Dict[str, List[str]] = None
    main_text: str = ""
    cta_elements: List[Dict[str, str]] = None
    form_elements: List[Dict[str, Any]] = None
    images: List[Dict[str, str]] = None
    links: List[Dict[str, str]] = None
    structured_data: List[Dict] = None
    page_structure: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.headings is None:
            self.headings = {}
        if self.cta_elements is None:
            self.cta_elements = []
        if self.form_elements is None:
            self.form_elements = []
        if self.images is None:
            self.images = []
        if self.links is None:
            self.links = []
        if self.structured_data is None:
            self.structured_data = []
        if self.page_structure is None:
            self.page_structure = {}


class WebExtractor:
    """Webコンテンツ抽出器"""
    
    def __init__(self, browser_timeout: int = 30000, 
                 wait_timeout: int = 10000,
                 user_agent: str = None):
        self.browser_timeout = browser_timeout
        self.wait_timeout = wait_timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.browser: Optional[Browser] = None
    
    async def __aenter__(self):
        """コンテキストマネージャー開始"""
        self.playwright = await async_playwright().__aenter__()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了"""
        if self.browser:
            await self.browser.close()
        await self.playwright.__aexit__(exc_type, exc_val, exc_tb)
    
    async def extract_content(self, url: str) -> ExtractedContent:
        """URLからコンテンツを抽出"""
        if not self.browser:
            raise RuntimeError("WebExtractor not initialized. Use async with.")
        
        page = await self.browser.new_page(
            user_agent=self.user_agent
        )
        
        try:
            # ページロード
            await page.goto(url, timeout=self.browser_timeout, 
                          wait_until="networkidle")
            
            # ページが完全に読み込まれるまで待機
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)  # 追加待機
            
            # HTMLコンテンツ取得
            html_content = await page.content()
            
            # BeautifulSoupでパース
            soup = BeautifulSoup(html_content, 'lxml')
            
            # コンテンツ抽出
            content = ExtractedContent(url=url)
            
            content.title = self._extract_title(soup)
            content.meta_description = self._extract_meta_description(soup)
            content.headings = self._extract_headings(soup)
            content.main_text = self._extract_main_text(soup)
            content.cta_elements = await self._extract_cta_elements(page, soup)
            content.form_elements = self._extract_form_elements(soup)
            content.images = self._extract_images(soup, url)
            content.links = self._extract_links(soup, url)
            content.structured_data = self._extract_structured_data(soup)
            content.page_structure = self._analyze_page_structure(soup)
            
            return content
            
        finally:
            await page.close()
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """タイトル抽出"""
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ""
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """メタディスクリプション抽出"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
        
        # OGディスクリプションも確認
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            return og_desc.get('content', '').strip()
        
        return ""
    
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """見出し抽出"""
        headings = {}
        
        for level in range(1, 7):  # h1-h6
            tag_name = f'h{level}'
            heading_tags = soup.find_all(tag_name)
            
            if heading_tags:
                headings[tag_name] = [
                    self._clean_text(tag.get_text()) 
                    for tag in heading_tags
                ]
        
        return headings
    
    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """メインテキスト抽出"""
        # 不要なタグを除去
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 
                        'aside', 'advertisement']):
            tag.decompose()
        
        # メインコンテンツエリアを特定
        main_candidates = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', class_=re.compile(r'content|main|body')),
            soup.find('section', class_=re.compile(r'content|main|body')),
        ]
        
        main_element = None
        for candidate in main_candidates:
            if candidate:
                main_element = candidate
                break
        
        # メインエリアが見つからない場合はbody全体
        if not main_element:
            main_element = soup.find('body') or soup
        
        # テキスト抽出
        text = main_element.get_text(separator=' ', strip=True)
        return self._clean_text(text)
    
    async def _extract_cta_elements(self, page: Page, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """CTA要素抽出"""
        cta_elements = []
        
        # ボタン要素
        buttons = soup.find_all(['button', 'input'], type=['button', 'submit'])
        for button in buttons:
            text = self._clean_text(button.get_text() or button.get('value', ''))
            if text:
                cta_elements.append({
                    'type': 'button',
                    'text': text,
                    'class': ' '.join(button.get('class', [])),
                    'id': button.get('id', '')
                })
        
        # リンクボタン（CTA的なクラス名を持つa要素）
        cta_patterns = re.compile(r'btn|button|cta|call.to.action|signup|register|buy|purchase|order|download', re.I)
        cta_links = soup.find_all('a', class_=cta_patterns)
        
        for link in cta_links:
            text = self._clean_text(link.get_text())
            if text:
                cta_elements.append({
                    'type': 'link_button',
                    'text': text,
                    'href': link.get('href', ''),
                    'class': ' '.join(link.get('class', [])),
                    'id': link.get('id', '')
                })
        
        return cta_elements
    
    def _extract_form_elements(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """フォーム要素抽出"""
        forms = []
        
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'class': ' '.join(form.get('class', [])),
                'id': form.get('id', ''),
                'fields': []
            }
            
            # フォームフィールド
            for field in form.find_all(['input', 'textarea', 'select']):
                field_type = field.get('type', 'text')
                field_name = field.get('name', '')
                field_id = field.get('id', '')
                
                # ラベル検索
                label_text = ''
                if field_id:
                    label = soup.find('label', attrs={'for': field_id})
                    if label:
                        label_text = self._clean_text(label.get_text())
                
                form_data['fields'].append({
                    'type': field_type,
                    'name': field_name,
                    'id': field_id,
                    'label': label_text,
                    'placeholder': field.get('placeholder', ''),
                    'required': field.has_attr('required')
                })
            
            forms.append(form_data)
        
        return forms
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """画像抽出"""
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src:
                # 相対URLを絶対URLに変換
                absolute_url = urljoin(base_url, src)
                
                images.append({
                    'src': absolute_url,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'class': ' '.join(img.get('class', []))
                })
        
        return images
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """リンク抽出"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = self._clean_text(link.get_text())
            
            if href and text:
                # 相対URLを絶対URLに変換
                absolute_url = urljoin(base_url, href)
                
                links.append({
                    'href': absolute_url,
                    'text': text,
                    'title': link.get('title', ''),
                    'class': ' '.join(link.get('class', []))
                })
        
        return links
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """構造化データ抽出"""
        structured_data = []
        
        # JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except (json.JSONDecodeError, AttributeError):
                continue
        
        # Microdata (簡易版)
        for element in soup.find_all(attrs={'itemscope': True}):
            item_type = element.get('itemtype', '')
            if item_type:
                structured_data.append({
                    'type': 'microdata',
                    'itemtype': item_type,
                    'element': element.name
                })
        
        return structured_data
    
    def _analyze_page_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """ページ構造分析"""
        structure = {
            'has_header': bool(soup.find('header')),
            'has_nav': bool(soup.find('nav')),
            'has_main': bool(soup.find('main')),
            'has_aside': bool(soup.find('aside')),
            'has_footer': bool(soup.find('footer')),
            'section_count': len(soup.find_all('section')),
            'article_count': len(soup.find_all('article')),
            'div_count': len(soup.find_all('div')),
            'total_elements': len(soup.find_all()),
        }
        
        # ランディングページの特徴検出
        lp_indicators = {
            'has_hero_section': bool(soup.find(['section', 'div'], 
                                              class_=re.compile(r'hero|banner|jumbotron', re.I))),
            'has_pricing': bool(soup.find(['section', 'div'], 
                                        class_=re.compile(r'price|pricing|plan', re.I))),
            'has_testimonials': bool(soup.find(['section', 'div'], 
                                             class_=re.compile(r'testimonial|review|customer', re.I))),
            'has_features': bool(soup.find(['section', 'div'], 
                                         class_=re.compile(r'feature|benefit|advantage', re.I))),
            'form_count': len(soup.find_all('form')),
            'cta_button_count': len(soup.find_all(['button', 'a'], 
                                                 class_=re.compile(r'btn|cta|call', re.I)))
        }
        
        structure['lp_indicators'] = lp_indicators
        
        return structure
    
    def _clean_text(self, text: str) -> str:
        """テキストクリーニング"""
        if not text:
            return ""
        
        # 改行・タブを空白に変換
        text = re.sub(r'[\n\r\t]+', ' ', text)
        
        # 複数の空白を単一空白に
        text = re.sub(r'\s+', ' ', text)
        
        # 前後の空白除去
        return text.strip()


class ContentAnalyzer:
    """抽出されたコンテンツの分析"""
    
    @staticmethod
    def analyze_content_quality(content: ExtractedContent) -> Dict[str, Any]:
        """コンテンツ品質分析"""
        analysis = {
            'title_length': len(content.title),
            'meta_description_length': len(content.meta_description),
            'main_text_length': len(content.main_text),
            'word_count': len(content.main_text.split()) if content.main_text else 0,
            'heading_structure': {},
            'cta_count': len(content.cta_elements),
            'form_count': len(content.form_elements),
            'image_count': len(content.images),
            'link_count': len(content.links)
        }
        
        # 見出し構造分析
        for level, headings in content.headings.items():
            analysis['heading_structure'][level] = {
                'count': len(headings),
                'average_length': sum(len(h) for h in headings) / len(headings) if headings else 0
            }
        
        # SEO要素チェック
        analysis['seo_elements'] = {
            'has_title': bool(content.title),
            'has_meta_description': bool(content.meta_description),
            'has_h1': 'h1' in content.headings and len(content.headings['h1']) > 0,
            'title_length_ok': 30 <= len(content.title) <= 60,
            'meta_description_length_ok': 120 <= len(content.meta_description) <= 160,
            'images_with_alt': sum(1 for img in content.images if img.get('alt')) / max(len(content.images), 1)
        }
        
        return analysis
    
    @staticmethod
    def extract_keywords(content: ExtractedContent, min_length: int = 3) -> List[str]:
        """キーワード抽出（簡易版）"""
        if not content.main_text:
            return []
        
        # 英数字のみの単語を抽出
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.main_text.lower())
        
        # 頻出単語をカウント
        word_count = {}
        for word in words:
            if len(word) >= min_length:
                word_count[word] = word_count.get(word, 0) + 1
        
        # 頻度順でソート
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, count in sorted_words[:50]]  # 上位50語