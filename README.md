# LP Analyzer - Automated Affiliate Landing Page Analysis Tool

A Python tool that automatically analyzes landing pages for affiliate marketing campaigns, extracting essential information for content creation quickly and efficiently.

## Features Overview

### 🎯 Core Features
- **URL List Management**: Bulk import from CSV files with progress tracking
- **Content Extraction**: Final rendered HTML extraction using Playwright
- **AI Analysis**: Advanced analysis powered by OpenAI API
- **Report Generation**: Automated Markdown reports and integrated summaries
- **Error Management**: Detailed logging and retry functionality

### 📊 Analysis Components
1. **Persona Hypothesis Generation** - Target customer identification
2. **USP & Competitive Advantage Extraction** - Unique strengths and differentiators
3. **Benefit Analysis** - Functional and emotional benefit extraction
4. **Copywriting Technique Analysis** - AIDA, PAS, BEAF framework detection
5. **Article Structure Templates** - Guidelines for affiliate content creation

## Setup

### 1. Requirements
- Python 3.8 or higher
- OpenAI API Key

### 2. Installation
```bash
# Clone repository
git clone <repository-url>
cd affiliate-lp-analyzer

# Run setup script
python setup.py
```

### 3. Environment Configuration
Edit the `.env` file to configure your OpenAI API key:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Single URL Analysis
```bash
python main.py analyze https://example.com/landing-page
```

### Batch Analysis from CSV
```bash
# Sequential execution
python main.py batch data/input/urls.csv

# Parallel execution
python main.py batch data/input/urls.csv --batch

# Resume after interruption
python main.py batch data/input/urls.csv --resume
```

### Progress Check
```bash
python main.py status
```

### Reset Error States
```bash
python main.py reset --reset-errors
```

## CSV File Format

Create your URL list CSV file in the following format:

```csv
url,priority,category
https://example.com/lp1,high,health
https://example.com/lp2,medium,finance
https://example.com/lp3,low,education
```

Required columns:
- `url`: Target URL for analysis

Optional columns:
- `priority`: Priority level (high/medium/low)
- `category`: Category classification (any text)

## Output Files

### Individual Reports (Markdown)
Generate comprehensive reports for each URL including:
- Page overview (title, meta description, key metrics)
- Persona analysis (demographics, occupation, challenges)
- USP & competitive advantage analysis
- Benefit analysis (functional & emotional benefits)
- Copywriting technique analysis
- Affiliate content creation guidelines

### Integrated Summary Report
For multi-URL analysis, generates integrated reports containing:
- Analysis overview and statistics
- Common persona, USP, and keyword trends
- Industry-specific insights
- Affiliate strategy recommendations

### JSON Data
Structured analysis data output in JSON format

## Directory Structure

```
affiliate-lp-analyzer/
├── src/
│   ├── core/           # Job queue & progress management
│   ├── extractors/     # Web content extraction
│   ├── analyzers/      # AI analysis engine
│   ├── exporters/      # Report generation
│   └── utils/          # OpenAI API & logging
├── data/
│   ├── input/          # Input CSV files
│   ├── output/         # Output reports
│   └── temp/           # Temporary files & progress data
├── logs/               # Log files
├── templates/          # Prompt templates
├── config/             # Configuration files
├── main.py             # Main CLI interface
├── setup.py            # Setup script
└── requirements.txt    # Dependencies
```

## Configuration Options

### Default Settings (.env)
```env
# OpenAI API Configuration
OPENAI_API_KEY=your_api_key
DEFAULT_MODEL=o4-mini
MAX_TOKENS=4000
TEMPERATURE=0.3

# Rate Limiting
REQUESTS_PER_MINUTE=60
MAX_CONCURRENT_REQUESTS=5

# Browser Settings
BROWSER_TIMEOUT=30000
WAIT_FOR_SELECTOR_TIMEOUT=10000
```

## Cost Management

- Default model: o4-mini (OpenAI o1 reasoning model, cost-optimized)
- Estimated cost per URL: $0.01-0.05
- Rate limiting to avoid API restrictions
- Detailed cost tracking and reporting

## Troubleshooting

### Common Issues

1. **Playwright browser not found**
   ```bash
   python -m playwright install
   ```

2. **OpenAI API rate limit errors**
   - Adjust rate limiting settings in `.env` file
   - Reduce concurrent execution (`--max-concurrent` option)

3. **Memory issues**
   - Avoid `--batch` option for large URL sets
   - Split processing into smaller chunks

### Log Files
- Main log: `logs/lp_analyzer_YYYYMMDD.log`
- Error log: `logs/lp_analyzer_errors_YYYYMMDD.log`
- JSON log: `logs/lp_analyzer_YYYYMMDD.json`

## Development & Extension

### Custom Prompts
Add JSON files to the `templates/` directory to create custom analysis prompts.

### API Extensions
Support for additional AI services and custom analysis logic can be easily integrated.

## Command Reference

### Main Commands
```bash
# Analyze single URL
python main.py analyze <URL> [--output OUTPUT] [--format FORMAT]

# Batch process URLs from CSV
python main.py batch <CSV_FILE> [--batch] [--max-concurrent N] [--resume]

# Check current progress
python main.py status

# Reset job states
python main.py reset [--reset-errors]
```

### Options
- `--output, -o`: Specify output filename
- `--format, -f`: Output format (markdown/json/both)
- `--batch, -b`: Enable parallel execution
- `--max-concurrent, -c`: Maximum concurrent processes
- `--resume, -r`: Resume interrupted processing
- `--verbose, -v`: Enable verbose logging
- `--log-level`: Set log level (DEBUG/INFO/WARNING/ERROR)

## API Integration

### OpenAI Models Supported
- o4-mini (default, OpenAI o1 reasoning model, cost-optimized)

### Rate Limiting Features
- Automatic request throttling
- Token usage tracking
- Exponential backoff retry logic
- Cost estimation and reporting

## Analysis Templates

The system includes pre-built analysis templates for:

1. **Persona Analysis**
   - Demographics and psychographics
   - Pain points and motivations
   - Information consumption behavior

2. **USP Extraction**
   - Unique value propositions
   - Competitive differentiators
   - Supporting evidence

3. **Benefit Analysis**
   - Functional vs emotional benefits
   - Power words and key phrases
   - Urgency and scarcity elements

4. **Copywriting Analysis**
   - Framework detection (AIDA, PAS, BEAF)
   - Social proof elements
   - Authority and credibility signals

## Performance Optimization

### Processing Speed
- Concurrent URL processing
- Intelligent content chunking
- Efficient DOM parsing
- Progress persistence for large batches

### Resource Management
- Memory-efficient content extraction
- API rate limiting compliance
- Automatic error recovery
- Detailed performance metrics

## Data Privacy & Security

- No personal data storage
- Secure API key handling
- Local processing (no data sent to third parties except OpenAI)
- Configurable data retention policies

## Contributing

We welcome contributions! Please see our contributing guidelines for:
- Code style requirements
- Testing procedures
- Documentation standards
- Issue reporting

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, feature requests, or questions:
- Create an issue on GitHub
- Check existing documentation
- Review troubleshooting guide

## Changelog

### Version 1.0.0
- Initial release
- Full LP analysis pipeline
- CLI interface
- Markdown report generation
- Error handling and logging
- Progress tracking and resume functionality

---

**Note**: This tool is designed for legitimate affiliate marketing research and content creation. Please ensure compliance with website terms of service and applicable laws when analyzing third-party landing pages.