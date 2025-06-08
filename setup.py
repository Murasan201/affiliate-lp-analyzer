#!/usr/bin/env python3
"""
LP Analyzer Setup Script
アフィリエイトLP自動分析ツールのセットアップ
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """必要なパッケージをインストール"""
    print("Installing Python packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def install_playwright_browsers():
    """Playwrightブラウザをインストール"""
    print("Installing Playwright browsers...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install"])

def create_env_file():
    """環境変数設定ファイルを作成"""
    env_file = Path(".env")
    if not env_file.exists():
        print("Creating .env file...")
        env_content = """# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Default settings
DEFAULT_MODEL=gpt-4-mini
MAX_TOKENS=4000
TEMPERATURE=0.3

# Rate limiting
REQUESTS_PER_MINUTE=60
MAX_CONCURRENT_REQUESTS=5

# Browser settings
BROWSER_TIMEOUT=30000
WAIT_FOR_SELECTOR_TIMEOUT=10000
"""
        env_file.write_text(env_content)
        print("Please edit .env file and set your OPENAI_API_KEY")

def create_sample_files():
    """サンプルファイルを作成"""
    # サンプルURLリスト
    sample_urls = Path("data/input/sample_urls.csv")
    if not sample_urls.exists():
        print("Creating sample URL list...")
        sample_content = """url,priority,category
https://example.com/lp1,high,health
https://example.com/lp2,medium,finance
https://example.com/lp3,low,education
"""
        sample_urls.write_text(sample_content)

def main():
    """メインセットアップ処理"""
    print("=== LP Analyzer Setup ===")
    
    try:
        install_requirements()
        install_playwright_browsers()
        create_env_file()
        create_sample_files()
        
        print("\n✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit .env file and set your OPENAI_API_KEY")
        print("2. Add URLs to data/input/urls.csv")
        print("3. Run: python main.py --help")
        
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()