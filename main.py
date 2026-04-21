from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from typing import Optional, TypedDict, Annotated
import re
import os
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

app = FastAPI(title="SEC Financial Data API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "FinancialDataApp contact@example.com",
    "Accept": "application/json",
}

CONCEPT_MAP = {
    "income_statement": {
        "TotalRevenues": [
            "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet", "SalesRevenueGoodsNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
            "NetRevenues",
        ],
        "CostOfSales": [
            "CostOfRevenue", "CostOfGoodsSold", "CostOfGoodsAndServicesSold", "CostOfSales",
        ],
        "GrossProfit": [
            "GrossProfit",
        ],
        "SGA_Expense": [
            "SellingGeneralAndAdministrativeExpense",
        ],
        "RD_Expense": [
            "ResearchAndDevelopmentExpense",
        ],
        "OperatingProfit": [
            "OperatingIncomeLoss",
        ],
        "NonOperatingIncome": [
            "NonoperatingIncomeExpense",
        ],
        "IncomeBeforeTaxes": [
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        ],
        "ProvisionForIncomeTaxes": [
            "IncomeTaxExpenseBenefit",
        ],
        "ConsolidatedNetIncome": [
            "NetIncomeLoss", "ProfitLoss",
        ],
        "NetIncomeCommon": [
            "NetIncomeLossAvailableToCommonStockholdersBasic",
        ],
        "BasicEPS": [
            "EarningsPerShareBasic",
        ],
        "DilutedEPS": [
            "EarningsPerShareDiluted",
        ],
        "BasicWeightedShares": [
            "WeightedAverageNumberOfSharesOutstandingBasic",
        ],
        "TotalSharesOutstanding": [
            "CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"
        ],
        "DilutedWeightedShares": [
            "WeightedAverageNumberOfDilutedSharesOutstanding",
        ],
        "DepreciationAmortization": [
            "DepreciationAndAmortization", "Depreciation",
        ],
    },
    "balance_sheet": {
        # ASSETS
        "Cash": [
            "CashAndCashEquivalentsAtCarryingValue",
        ],
        "ShortTermInvestments": [
            "ShortTermInvestments", 
            "MarketableSecuritiesCurrent", 
            "AvailableForSaleSecuritiesCurrent", 
            "AvailableForSaleSecuritiesDebtSecuritiesCurrent"
        ],
        "TotalCashAndCashEquivalents": [
            "CashCashEquivalentsAndShortTermInvestments"
        ],
        "AccountsReceivable": [
            "AccountsReceivableNetCurrent",
        ],
        "TotalTradeReceivables": [
            "AccountsReceivableNetCurrent",
        ],
        "Inventory": ["InventoryNet"],
        "OtherCurrentAssets": ["OtherAssetsCurrent"],
        "CurrentAssets": ["AssetsCurrent"],
        "PPE_Net": [
            "PropertyPlantAndEquipmentNet",
        ],
        "Goodwill": ["Goodwill"],
        "OtherLongTermAssets": ["OtherAssetsNoncurrent", "IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet"],
        "TotalAssets": ["Assets"],

        # LIABILITIES
        "AccountsPayable": ["AccountsPayableCurrent"],
        "AccruedExpenses": ["AccruedLiabilitiesCurrent", "OtherAccruedLiabilitiesCurrent"],
        "CurrentPortionLongTermDebt": ["LongTermDebtCurrent"],
        "UnearnedRevenue": ["DeferredRevenueCurrent", "ContractWithCustomerLiabilityCurrent"],
        "CurrentLiabilities": ["LiabilitiesCurrent"],
        "LongTermDebt": ["LongTermDebtNoncurrent", "LongTermDebt"],
        "Leases": ["OperatingLeaseLiabilityNoncurrent", "FinanceLeaseLiabilityNoncurrent"],
        "OtherLongTermLiabilities": ["OtherLiabilitiesNoncurrent"],
        "TotalLongTermLiabilities": ["LiabilitiesNoncurrent"],
        "TotalLiabilities": ["Liabilities"],

        # EQUITY
        "PreferredStock": ["PreferredStockValue"],
        "CommonStock": ["CommonStockValue"],
        "TreasuryStock": ["TreasuryStockValue"],
        "AdditionalPaidInCapital": ["AdditionalPaidInCapital", "AdditionalPaidInCapitalCommonStock"],
        "AccumulatedOtherComprehensiveIncome": ["AccumulatedOtherComprehensiveIncomeLossNetOfTax"],
        "RetainedEarnings": ["RetainedEarningsAccumulatedDeficit"],
        "TotalCommonShareholdersEquity": ["StockholdersEquity"],
        "TotalEquity": [
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            "StockholdersEquity"
        ],
        "TotalLiabilitiesAndEquity": ["LiabilitiesAndStockholdersEquity"],
    },
    "cash_flow": {
        "OperatingCashFlow": [
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        ],
        "InvestingCashFlow": [
            "NetCashProvidedByUsedInInvestingActivities",
            "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations",
        ],
        "FinancingCashFlow": [
            "NetCashProvidedByUsedInFinancingActivities",
            "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations",
        ],
        "CapEx": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsForCapitalImprovements",
        ],
        "FreeCashFlow_Proxy": [
            "NetCashProvidedByUsedInOperatingActivities",
        ],
        "DividendsPaid": [
            "PaymentsOfDividends", "PaymentsOfDividendsCommonStock",
        ],
        "ShareRepurchases": [
            "PaymentsForRepurchaseOfCommonStock",
        ],
        "DebtIssuance": [
            "ProceedsFromIssuanceOfLongTermDebt",
        ],
        "DebtRepayment": [
            "RepaymentsOfLongTermDebt",
        ],
        "DepreciationInCF": [
            "DepreciationDepletionAndAmortization",
        ],
        "StockBasedComp": [
            "ShareBasedCompensation",
        ],
        "Acquisitions": [
            "PaymentsToAcquireBusinessesNetOfCashAcquired",
        ],
        "CashBeginningOfPeriod": [
            "CashAndCashEquivalentsAtCarryingValue",
        ],
        "NetChangeInCash": [
            "CashAndCashEquivalentsPeriodIncreaseDecrease",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
        ],
    },
}


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], "messages"]
    context: str

def get_llm():
    try:
        # Using Zephyr-7B-Beta as it's an ungated model that generally works without an API key on HF's free inference API
        llm = HuggingFaceEndpoint(
            repo_id="HuggingFaceH4/zephyr-7b-beta",
            temperature=0.1,
            max_new_tokens=1024,
        )
        return ChatHuggingFace(llm=llm)
    except Exception as e:
        # Fallback to another ungated model
        llm = HuggingFaceEndpoint(
            repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            temperature=0.1,
            max_new_tokens=1024,
        )
        return ChatHuggingFace(llm=llm)

def analyze_financials(state: ChatState):
    llm = get_llm()
    sys_msg = SystemMessage(content=f"You are an expert financial analyst. Use the following SEC financial data to answer the user's question.\n\nContext:\n{state['context']}\n\nUse Chain of Thought reasoning in your response and output markdown format.")
    
    response = llm.invoke([sys_msg] + state["messages"])
    return {"messages": [response]}

workflow = StateGraph(ChatState)
workflow.add_node("analyze", analyze_financials)
workflow.set_entry_point("analyze")
workflow.add_edge("analyze", END)
qa_app = workflow.compile()

class MessageDict(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[MessageDict]


async def get_cik(ticker: str) -> str:
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2000-01-01&enddt=2024-12-31&forms=10-K"
    # Use the ticker lookup endpoint
    lookup_url = f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=10&search_text=&action=getcompany&output=atom"
    
    # Try the company_tickers JSON
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(tickers_url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            for key, val in data.items():
                if val.get("ticker", "").upper() == ticker.upper():
                    cik = str(val["cik_str"]).zfill(10)
                    return cik
    raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found in SEC database")


async def get_company_facts(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url, headers=HEADERS)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch company facts from SEC")
        return resp.json()


def extract_annual_data(facts: dict, concept_aliases: list) -> dict:
    """Extract annual (10-K) data for a concept, trying multiple aliases."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    
    merged_annual = {}
    for alias in reversed(concept_aliases):
        if alias not in us_gaap:
            continue
        concept = us_gaap[alias]
        units = concept.get("units", {})
        
        # Try USD first, then shares, then pure
        for unit_key in ["USD", "shares", "USD/shares", "pure"]:
            if unit_key not in units:
                continue
            entries = units[unit_key]
            # Filter for 10-K annual filings, prefer non-amended
            annual = {}
            for e in entries:
                form = e.get("form", "")
                if form not in ("10-K", "10-K/A", "20-F"):
                    continue
                if e.get("fp") != "FY":
                    continue
                year = e.get("end", "")[:4]
                if not year.isdigit():
                    continue
                # Prefer most recent filing for the year
                if year not in annual or e.get("filed", "") > annual[year].get("filed", ""):
                    annual[year] = e
            if annual:
                for yr, v in annual.items():
                    merged_annual[yr] = v["val"]
                break
    return merged_annual


def extract_quarterly_data(facts: dict, concept_aliases: list) -> dict:
    """Extract quarterly data for a concept."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    
    merged_quarterly = {}
    for alias in reversed(concept_aliases):
        if alias not in us_gaap:
            continue
        concept = us_gaap[alias]
        units = concept.get("units", {})
        
        for unit_key in ["USD", "shares", "USD/shares", "pure"]:
            if unit_key not in units:
                continue
            entries = units[unit_key]
            quarterly = {}
            for e in entries:
                form = e.get("form", "")
                if form not in ("10-Q", "10-K"):
                    continue
                period_key = f"{e.get('end', '')}_{e.get('form', '')}_{e.get('fp', '')}"
                end_date = e.get("end", "")
                if not end_date:
                    continue
                # For quarters, use end_date mapping
                if end_date not in quarterly or e.get("filed", "") > quarterly[end_date].get("filed", ""):
                    quarterly[end_date] = e
            if quarterly:
                for qd, v in quarterly.items():
                    merged_quarterly[qd] = v["val"]
                break
    return merged_quarterly


@app.get("/api/ticker/{ticker}/info")
async def get_company_info(ticker: str):
    ticker = ticker.upper().strip()
    cik = await get_cik(ticker)
    
    # Get submissions for company name
    sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(sub_url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "ticker": ticker,
                "cik": cik,
                "name": data.get("name", ticker),
                "sic": data.get("sic", ""),
                "sic_description": data.get("sicDescription", ""),
                "state": data.get("stateOfIncorporation", ""),
                "fiscal_year_end": data.get("fiscalYearEnd", ""),
                "exchanges": data.get("exchanges", []),
            }
    return {"ticker": ticker, "cik": cik, "name": ticker}


@app.get("/api/ticker/{ticker}/financials")
async def get_financials(ticker: str):
    ticker = ticker.upper().strip()
    cik = await get_cik(ticker)
    facts = await get_company_facts(cik)
    
    result = {
        "income_statement": {},
        "balance_sheet": {},
        "cash_flow": {},
    }
    
    for statement, concepts in CONCEPT_MAP.items():
        for metric, aliases in concepts.items():
            annual = extract_annual_data(facts, aliases)
            if annual:
                result[statement][metric] = annual
    
    # Compute free cash flow
    ocf = result["cash_flow"].get("OperatingCashFlow", {})
    capex = result["cash_flow"].get("CapEx", {})
    if ocf:
        result["cash_flow"]["FreeCashFlow"] = {
            yr: ocf[yr] - abs(capex.get(yr, 0))
            for yr in ocf
        }
    
    # Build year list
    all_years = set()
    for statement in result.values():
        for metric_data in statement.values():
            all_years.update(metric_data.keys())
    
    sorted_years = sorted(all_years)
    # Filter to last 20 years
    from datetime import datetime
    cutoff = str(datetime.now().year - 20)
    sorted_years = [y for y in sorted_years if y >= cutoff]
    
    return {
        "ticker": ticker,
        "cik": cik,
        "years": sorted_years,
        "statements": result,
    }


@app.get("/api/ticker/{ticker}/quarterly")
async def get_quarterly(ticker: str, statement: str = "income_statement"):
    ticker = ticker.upper().strip()
    cik = await get_cik(ticker)
    facts = await get_company_facts(cik)
    
    concepts = CONCEPT_MAP.get(statement, {})
    result = {}
    
    for metric, aliases in concepts.items():
        quarterly = extract_quarterly_data(facts, aliases)
        if quarterly:
            # Last 5 years of quarters
            from datetime import datetime
            cutoff = str(datetime.now().year - 5)
            filtered = {k: v for k, v in quarterly.items() if k[:4] >= cutoff}
            if filtered:
                result[metric] = filtered
    
    periods = set()
    for v in result.values():
        periods.update(v.keys())
    
    return {
        "ticker": ticker,
        "statement": statement,
        "periods": sorted(periods),
        "data": result,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/ticker/{ticker}/chat")
async def chat_with_data(ticker: str, req: ChatRequest):
    ticker = ticker.upper().strip()
    
    try:
        cik = await get_cik(ticker)
        facts = await get_company_facts(cik)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    result = {
        "income_statement": {},
        "balance_sheet": {},
        "cash_flow": {},
    }
    
    for statement, concepts in CONCEPT_MAP.items():
        for metric, aliases in concepts.items():
            annual = extract_annual_data(facts, aliases)
            if annual:
                result[statement][metric] = annual
                
    context_str = f"Financial Data for {ticker}:\n"
    for stmt, st_data in result.items():
        if not st_data:
            continue
        context_str += f"\n--- {stmt.upper()} ---\n"
        for metric, annual in st_data.items():
            sorted_years = sorted(list(annual.keys()))
            # Only include last 10 years to save context size, users usually ask recent questions
            sorted_years = sorted_years[-10:]
            data_str = ", ".join([f"{y}: {annual[y]}" for y in sorted_years])
            context_str += f"{metric}: {data_str}\n"

    lc_messages = []
    for m in req.messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))
            
    state = {"messages": lc_messages, "context": context_str}
    
    try:
        final_state = qa_app.invoke(state)
        return {"response": final_state["messages"][-1].content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")
