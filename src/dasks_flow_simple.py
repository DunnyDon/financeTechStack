"""Simple Dask flow examples."""

from datetime import datetime
from prefect import flow, task, get_run_logger
from src.dask_integration import DaskClientManager, parallel_compute


@flow(name="portfolio_prices_dask")
def fetch_portfolio_prices_dask():
    """Fetch portfolio prices using Dask."""
    from src.portfolio_holdings import Holdings
    
    logger = get_run_logger()
    logger.info("Fetching portfolio prices with Dask")
    
    # Load portfolio
    holdings = Holdings("holdings.csv")
    tickers = holdings.all_holdings['sym'].tolist()
    
    logger.info(f"Fetching prices for {len(tickers)} tickers")
    
    def fetch_price(ticker):
        """Fetch single price (runs on Dask worker)."""
        try:
            import yfinance as yf
            data = yf.download(ticker, period="1d", progress=False)
            return {ticker: float(data["Close"].iloc[-1])}
        except Exception as e:
            return {ticker: None}
    
    # Use parallel_compute
    results = parallel_compute(tickers, fetch_price)
    
    # Combine results
    prices = {}
    for r in results:
        if r:
            prices.update(r)
    
    logger.info(f"Fetched {len(prices)} prices")
    return prices


if __name__ == "__main__":
    
    # Run portfolio prices
    prices = fetch_portfolio_prices_dask()
    print(f"✓ Portfolio prices: {prices}")