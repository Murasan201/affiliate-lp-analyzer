# LP Analyzer - アフィリエイトLP自動分析ツール

ASPで取り扱う案件のランディングページを自動分析し、アフィリエイト記事作成に必要な情報を迅速かつ効率的に抽出・提示するPythonツールです。

## 機能概要

### 🎯 主要機能
- **URLリスト管理**: CSVファイルからURL一括インポート、進捗管理
- **コンテンツ抽出**: Playwrightによる最終レンダリングHTML取得
- **AI分析**: OpenAI APIを使用した高度な分析
- **レポート生成**: Markdownレポートと統合サマリの自動生成
- **エラー管理**: 詳細ログとリトライ機能

### 📊 分析内容
1. **ペルソナ仮説生成** - ターゲット顧客層の特定
2. **USP・競合優位性抽出** - 独自の強みと差別化ポイント
3. **ベネフィット分析** - 機能的・感情的ベネフィットの抽出
4. **コピーライティング手法** - AIDA、PAS、BEAFなどの手法分析
5. **記事構成テンプレート** - アフィリエイト記事作成の指針

## セットアップ

### 1. 環境要件
- Python 3.8以上
- OpenAI APIキー

### 2. インストール
```bash
# リポジトリクローン
git clone <repository-url>
cd affiliate-lp-analyzer

# セットアップスクリプト実行
python setup.py
```

### 3. 環境変数設定
`.env`ファイルを編集してOpenAI APIキーを設定：
```env
OPENAI_API_KEY=your_openai_api_key_here
```

## 使用方法

### 単一URL分析
```bash
python main.py analyze https://example.com/landing-page
```

### CSVファイルから一括分析
```bash
# 順次実行
python main.py batch data/input/urls.csv

# 並列実行
python main.py batch data/input/urls.csv --batch

# 中断後の再開
python main.py batch data/input/urls.csv --resume
```

### 進捗確認
```bash
python main.py status
```

### エラー状態のリセット
```bash
python main.py reset --reset-errors
```

## CSVファイル形式

URLリストのCSVファイルは以下の形式で作成してください：

```csv
url,priority,category
https://example.com/lp1,high,health
https://example.com/lp2,medium,finance
https://example.com/lp3,low,education
```

必須列：
- `url`: 分析対象のURL

オプション列：
- `priority`: 優先度（high/medium/low）
- `category`: カテゴリ（任意のテキスト）

## 出力ファイル

### 個別レポート（Markdown）
各URLごとに以下の内容を含むレポートを生成：
- ページ概要（タイトル、メタディスクリプション、基本指標）
- ペルソナ分析（年齢層、職業、課題など）
- USP・競合優位性分析
- ベネフィット分析（機能的・感情的ベネフィット）
- コピーライティング手法分析
- アフィリエイト記事作成のポイント

### 統合サマリレポート
複数URL分析時に以下を含む統合レポートを生成：
- 分析概要と統計
- 共通ペルソナ・USP・キーワード傾向
- 業界別インサイト
- アフィリエイト戦略提案

### JSONデータ
構造化された分析データをJSON形式で出力

## ディレクトリ構造

```
affiliate-lp-analyzer/
├── src/
│   ├── core/           # ジョブキュー・進捗管理
│   ├── extractors/     # Webコンテンツ抽出
│   ├── analyzers/      # AI分析エンジン
│   ├── exporters/      # レポート生成
│   └── utils/          # OpenAI API・ログ管理
├── data/
│   ├── input/          # 入力CSVファイル
│   ├── output/         # 出力レポート
│   └── temp/           # 一時ファイル・進捗データ
├── logs/               # ログファイル
├── templates/          # プロンプトテンプレート
├── config/             # 設定ファイル
├── main.py             # メインCLI
├── setup.py            # セットアップスクリプト
└── requirements.txt    # 依存パッケージ
```

## 設定オプション

### デフォルト設定（.env）
```env
# OpenAI API設定
OPENAI_API_KEY=your_api_key
DEFAULT_MODEL=gpt-4o-mini
MAX_TOKENS=4000
TEMPERATURE=0.3

# レート制限
REQUESTS_PER_MINUTE=60
MAX_CONCURRENT_REQUESTS=5

# ブラウザ設定
BROWSER_TIMEOUT=30000
WAIT_FOR_SELECTOR_TIMEOUT=10000
```

## コスト管理

- デフォルトモデル：GPT-4o-mini（コスト効率重視）
- 1URLあたりの概算コスト：$0.01-0.05
- レート制限対応でAPI制限を回避
- 詳細なコスト追跡とレポート出力

## トラブルシューティング

### よくある問題

1. **Playwrightブラウザが見つからない**
   ```bash
   python -m playwright install
   ```

2. **OpenAI API制限エラー**
   - `.env`ファイルでレート制限設定を調整
   - 並列実行数を減らす（`--max-concurrent`オプション）

3. **メモリ不足**
   - 大量のURL処理時は`--batch`オプションを避ける
   - 処理を分割して実行

### ログファイル
- メインログ：`logs/lp_analyzer_YYYYMMDD.log`
- エラーログ：`logs/lp_analyzer_errors_YYYYMMDD.log`
- JSONログ：`logs/lp_analyzer_YYYYMMDD.json`

## 開発・拡張

### カスタムプロンプト
`templates/`ディレクトリにJSONファイルを追加することで、独自の分析プロンプトを作成できます。

### API拡張
OpenAI以外のAIサービス対応やカスタム分析ロジックの追加が可能です。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## サポート

問題や要望がございましたら、GitHubのIssuesページまでお報告ください。