import urllib.request
import json

def search_ticker_suggestions(query):
    """
    Sucht nach Ticker-Symbolen basierend auf Firmenname oder Ticker-Query.
    Nutzt die öffentliche Yahoo Finance Autocomplete API.
    """
    if not query or len(query.strip()) < 1:
        return []
    
    query = query.strip()
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=10&newsCount=0"
    
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            quotes = data.get('quotes', [])
            
            results = []
            for q in quotes:
                symbol = q.get('symbol')
                shortname = q.get('shortname') or q.get('longname', 'Unbekannt')
                exch = q.get('exchange', '')
                qtype = q.get('quoteType', '')
                
                # Wir filtern primär nach Aktien (EQUITY) oder ETFs, um Müll zu vermeiden
                if symbol and qtype in ['EQUITY', 'ETF']:
                    results.append({
                        "symbol": symbol,
                        "name": shortname,
                        "exchange": exch,
                        "display": f"{symbol} – {shortname} ({exch})"
                    })
            return results
    except Exception as e:
        print(f"Fehler bei Tickersuche: {e}")
        return []
