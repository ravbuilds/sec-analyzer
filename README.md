# SEC Financial Explorer

Extract 20 years of financial data from SEC EDGAR 10-K filings directly — no API key required.

## Features

- **Income Statement**: Revenue, Gross Profit, Operating Income, Net Income, EPS, R&D, SG&A, EBIT, D&A, Tax, Interest, and more
- **Balance Sheet**: Total Assets, Liabilities, Equity, Cash, Debt, PP&E, Goodwill, Inventory, Receivables, and more
- **Cash Flow Statement**: Operating/Investing/Financing CF, Free Cash Flow, CapEx, Dividends, Buybacks, and more
- Interactive charts (line, bar, area) — select up to 4 metrics at once
- CSV export for any statement
- Data directly from SEC EDGAR XBRL API (no rate limits for reasonable use)

## Requirements

- Python 3.8+

## Quick Start

```bash
chmod +x start.sh
./start.sh
```

Then open **http://localhost:3000** in your browser.

## Manual Start

### Backend (Terminal 1)
```bash
#### Activate Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

#### Install Dependencies
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Terminal 2)
```bash
python3 -m http.server 3000
```

Open **http://localhost:3000**

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/ticker/{ticker}/info` | Company info (name, SIC, exchange) |
| `GET /api/ticker/{ticker}/financials` | Full annual financials (20 years) |
| `GET /api/ticker/{ticker}/quarterly?statement=income_statement` | Quarterly data (5 years) |
| `GET /docs` | Interactive API documentation |

## How It Works

1. Resolves ticker → CIK using SEC's company tickers JSON
2. Fetches XBRL company facts from `data.sec.gov`
3. Extracts annual 10-K data per metric with intelligent alias fallbacks
4. Computes derived metrics (Free Cash Flow = OCF − CapEx)

## Supported Tickers

Any company that files with the SEC (US-listed stocks). Examples:
`AAPL`, `MSFT`, `GOOGL`, `AMZN`, `NVDA`, `META`, `TSLA`, `JPM`, `JNJ`, `BRK-B`

## Notes

- SEC EDGAR rate limits: ~10 req/sec. The app fetches 2 calls per ticker.
- Some metrics may be missing for older filings (pre-2009 XBRL adoption)
- Fiscal year end varies by company (not always December)
