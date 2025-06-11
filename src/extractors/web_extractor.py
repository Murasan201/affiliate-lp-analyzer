"""
Web content extraction using Playwright
ヘッドレスブラウザによる最終レンダリングHTML取得とコンテンツ抽出
"""

import asyncio
import re
import random
import requests
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
    
    def __init__(self, browser_timeout: int = 45000, 
                 wait_timeout: int = 15000,
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
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了"""
        if self.browser:
            await self.browser.close()
        await self.playwright.__aexit__(exc_type, exc_val, exc_tb)
    
    async def extract_content(self, url: str) -> ExtractedContent:
        """URLからコンテンツを抽出（複数戦略フォールバック付き）"""
        # 戦略1: Playwrightによる高度なボット回避
        try:
            return await self._extract_with_playwright(url)
        except Exception as e:
            print(f"⚠️ Playwright抽出失敗: {e}")
            
        # 戦略2: requestsライブラリによるフォールバック
        try:
            return await self._extract_with_requests(url)
        except Exception as e:
            print(f"⚠️ requests抽出失敗: {e}")
            
        # 戦略3: 基本的なHTTPリクエスト（最終フォールバック）
        try:
            return await self._extract_basic_fallback(url)
        except Exception as e:
            print(f"❌ 全ての抽出戦略が失敗: {e}")
            raise RuntimeError(f"コンテンツ抽出に失敗しました: {url}")
    
    async def _extract_with_playwright(self, url: str) -> ExtractedContent:
        """Playwrightによる高度なボット回避抽出"""
        if not self.browser:
            raise RuntimeError("WebExtractor not initialized. Use async with.")
        
        # ランダムなユーザーエージェントを選択
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        
        selected_ua = random.choice(user_agents)
        
        # コンテキストを作成（ユーザーエージェントとビューポート設定）
        context = await self.browser.new_context(
            user_agent=selected_ua,
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        )
        
        page = await context.new_page()
        
        # 高度なボット検出回避スクリプト
        await page.add_init_script("""
            // webdriverプロパティを隠す
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // languagesプロパティを設定
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ja', 'en-US', 'en'],
            });
            
            // pluginsプロパティを偽装
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // webglプロパティを偽装
            const getParameter = WebGLRenderingContext.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
            
            // chrome objectを追加
            window.chrome = {
                runtime: {},
            };
            
            // permissions APIを偽装
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        try:
            # ランダムな遅延でページロード
            await asyncio.sleep(random.uniform(1, 3))
            
            # ページロード（複数の戦略を試す）
            try:
                await page.goto(url, timeout=self.browser_timeout, 
                              wait_until="networkidle")
            except Exception as e:
                print(f"⚠️ networkidle失敗、domcontentloadedで再試行: {e}")
                await page.goto(url, timeout=self.browser_timeout, 
                              wait_until="domcontentloaded")
            
            # 人間らしい行動をシミュレート
            await asyncio.sleep(random.uniform(2, 4))
            
            # マウスの動きをシミュレート
            await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await page.mouse.move(random.randint(200, 900), random.randint(200, 700))
            
            # スクロール動作をシミュレート
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 4)")
            await asyncio.sleep(random.uniform(1, 2))
            await page.evaluate("window.scrollTo(0, 0)")
            
            # ページが完全に読み込まれるまで待機
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(random.uniform(1, 3))
            
            # HTMLコンテンツ取得
            html_content = await page.content()
            
            return await self._process_html_content(html_content, url, page)
            
        finally:
            await context.close()
    
    async def _extract_with_requests(self, url: str) -> ExtractedContent:
        """requestsライブラリによる抽出（複数回リトライ付き）"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # 5回リトライ
        for attempt in range(5):
            try:
                headers['User-Agent'] = random.choice(user_agents)
                
                # ランダムな遅延
                await asyncio.sleep(random.uniform(1, 3))
                
                response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
                
                if response.status_code == 200:
                    return await self._process_html_content(response.text, url)
                elif response.status_code == 403:
                    print(f"⚠️ 403エラー (試行 {attempt + 1}/5): {url}")
                    if attempt < 4:  # 最後の試行でない場合
                        await asyncio.sleep(random.uniform(5, 10))  # より長い遅延
                        continue
                else:
                    raise requests.RequestException(f"HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️ requests試行 {attempt + 1}/5 失敗: {e}")
                if attempt < 4:
                    await asyncio.sleep(random.uniform(3, 7))
                    continue
                raise
        
        raise requests.RequestException("requests抽出の全ての試行が失敗")
    
    async def _extract_basic_fallback(self, url: str) -> ExtractedContent:
        """基本的なHTTPリクエスト（最終フォールバック）"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return await self._process_html_content(response.text, url)
        except Exception as e:
            print(f"❌ 基本フォールバック失敗: {e}")
            # 空のコンテンツを返す
            return ExtractedContent(url=url, title="抽出失敗", main_text="コンテンツの抽出に失敗しました")
    
    async def _process_html_content(self, html_content: str, url: str, page: Page = None) -> ExtractedContent:
        """HTMLコンテンツを処理してExtractedContentオブジェクトを生成"""
        # BeautifulSoupでパース
        soup = BeautifulSoup(html_content, 'lxml')
        
        # コンテンツ抽出
        content = ExtractedContent(url=url)
        
        content.title = self._extract_title(soup)
        content.meta_description = self._extract_meta_description(soup)
        content.headings = self._extract_headings(soup)
        content.main_text = self._extract_main_text(soup)
        content.cta_elements = await self._extract_cta_elements(page, soup) if page else self._extract_cta_elements_static(soup)
        content.form_elements = self._extract_form_elements(soup)
        content.images = self._extract_images(soup, url)
        content.links = self._extract_links(soup, url)
        content.structured_data = self._extract_structured_data(soup)
        content.page_structure = self._analyze_page_structure(soup)
        
        return content
    
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
        """CTA要素抽出（Playwright使用）"""
        if page:
            return self._extract_cta_elements_static(soup)
        else:
            return self._extract_cta_elements_static(soup)
    
    def _extract_cta_elements_static(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """CTA要素抽出（静的版）"""
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