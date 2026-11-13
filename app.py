import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json
import os
from pathlib import Path

# Importiere unsere Score-Module
from buy_and_hold_score import calculate_buy_and_hold_score, calculate_buy_and_hold_details
from buffett_score import calculate_buffett_score
from trading_score import calculate_trading_score
from fundamental_analysis import show_fundamental_analysis

# Importiere die erweiterte Chartanalyse (Dialog-Funktion)
try:
    from chart_analysis import show_chart_analysis_dialog
except ImportError:
    st.error("Konnte `chart_analysis.py` nicht finden. Stelle sicher, dass die Datei im selben Ordner liegt.")

# --- PAGE CONFIG ---
st.set_page_config(page_title="Aktien-Dashboard (EUR)", layout="wide")

# Alle Konfigurationsdateien liegen zentral im Home-Verzeichnis des Benutzers.
# Beispiel: /home/<user>/config/config.json
CONFIG_DIR = Path.cwd() / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"


def ensure_config_dir():
    """Legt ~/config bei Bedarf an."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def migrate_legacy_config():
    """Übernimmt eine bisherige ./config.json einmalig nach ~/config/config.json."""
    ensure_config_dir()
    legacy_file = Path.cwd() / "config.json"
    if not CONFIG_FILE.exists() and legacy_file.is_file():
        try:
            shutil.copy2(legacy_file, CONFIG_FILE)
        except OSError as exc:
            st.warning(f"Alte Konfiguration konnte nicht übernommen werden: {exc}")


migrate_legacy_config()

def load_config():
    default_config = {
        "active_category": "Tech",
        "categories": {
            "Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"],
            "Versorger": ["EOAN.DE", "RWE.DE", "JNJ", "PG"]
        },
        "chart_type": "Linie",
        "timeframe": "1mo",
        "cache_ttl_minutes": 60
    }

    ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "categories" in data:
                    return {
                        "active_category": data.get("active_category", "Tech"),
                        "categories": data.get("categories", default_config["categories"]),
                        "chart_type": data.get("chart_type", "Linie"),
                        "timeframe": data.get("timeframe", "1mo"),
                        "cache_ttl_minutes": data.get("cache_ttl_minutes", 60)
                    }
        except Exception:
            pass

    save_config(default_config)
    return default_config

def save_config(config_data):
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

if "config" not in st.session_state:
    st.session_state.config = load_config()

categories = st.session_state.config["categories"]
active_cat = st.session_state.config["active_category"]

if active_cat not in categories:
    active_cat = list(categories.keys())[0]
    st.session_state.config["active_category"] = active_cat

current_tickers = categories[active_cat]
cache_ttl_sec = int(st.session_state.config.get("cache_ttl_minutes", 60)) * 60

@st.cache_data(ttl=cache_ttl_sec)
def load_stock_data(ticker, period):
    """Lädt Verlaufs- und Fundamentaldaten und rechnet stabil in EUR um."""
    stock = yf.Ticker(ticker)

    # Intelligentes Intervall für aktuelle Daten
    if period == "1d":
        interval = "5m"
    elif period in ["5d", "7d"]:
        interval = "1h"
    else:
        interval = "1d"

    hist = stock.history(period=period, interval=interval)

    # Fallback falls leer
    if hist.empty:
        hist = stock.history(period=period, interval="1d")

    info = stock.info.copy()

    original_currency = info.get('currency', 'USD').upper()

    if original_currency != 'EUR' and not hist.empty:
        try:
            fx_ticker = f"EUR{original_currency}=X"
            fx_data = yf.Ticker(fx_ticker).history(period="5d")

            if not fx_data.empty:
                rate = fx_data['Close'].iloc[-1]
                if rate > 0:
                    for col in ['Open', 'High', 'Low', 'Close']:
                        if col in hist.columns:
                            hist[col] = hist[col] / rate

                    for key in ['previousClose', 'open', 'dayLow', 'dayHigh', 'fiftyTwoWeekLow', 'fiftyTwoWeekHigh', 'dividendRate', 'forwardEps', 'trailingEps']:
                        if key in info and info[key] is not None:
                            info[key] = info[key] / rate

            info['currency'] = 'EUR'
            info['original_currency'] = original_currency
        except Exception:
            pass

    return hist, info


# --- HEADER & SIDEBAR ---
st.title(f"📈 Aktien-Dashboard: {active_cat} (in EUR)")

st.sidebar.header("📂 Dashboard-Auswahl")

cat_names = list(categories.keys())
selected_cat_idx = cat_names.index(active_cat) if active_cat in cat_names else 0
chosen_category = st.sidebar.selectbox("Wähle ein Dashboard:", cat_names, index=selected_cat_idx)

if chosen_category != active_cat:
    st.session_state.config["active_category"] = chosen_category
    save_config(st.session_state.config)
    st.rerun()

if len(categories) < 4:
    with st.sidebar.expander("➕ Neues Dashboard erstellen"):
        new_cat_name = st.text_input("Name des Dashboards:").strip()
        if st.button("Dashboard anlegen"):
            if new_cat_name:
                if new_cat_name in categories:
                    st.warning("Existiert bereits!")
                else:
                    categories[new_cat_name] = ["AAPL"]
                    st.session_state.config["active_category"] = new_cat_name
                    save_config(st.session_state.config)
                    st.rerun()

if len(categories) > 1:
    if st.sidebar.button(f"🗑️ Dashboard '{active_cat}' löschen"):
        del categories[active_cat]
        st.session_state.config["active_category"] = list(categories.keys())[0]
        save_config(st.session_state.config)
        st.rerun()

st.sidebar.divider()
st.sidebar.header("⚙️ Allgemeine Einstellungen")

chart_options = ["Linie", "Fläche (Area)", "Candlestick"]
current_chart_idx = chart_options.index(st.session_state.config["chart_type"]) if st.session_state.config["chart_type"] in chart_options else 0
selected_chart_type = st.sidebar.selectbox("📊 Chart-Typ wählen:", chart_options, index=current_chart_idx)

timeframe_mapping = {
    "1 Tag (1d)": "1d",
    "1 Woche (5d)": "5d",
    "1 Monat (1mo)": "1mo",
    "3 Monate (3mo)": "3mo",
    "6 Monate (6mo)": "6mo",
    "1 Jahr (1y)": "1y",
    "5 Jahre (5y)": "5y"
}
tf_keys = list(timeframe_mapping.keys())
tf_vals = list(timeframe_mapping.values())
current_tf_idx = tf_vals.index(st.session_state.config["timeframe"]) if st.session_state.config["timeframe"] in tf_vals else 2
selected_tf_label = st.sidebar.selectbox("📅 Zeitfenster:", tf_keys, index=current_tf_idx)
selected_timeframe = timeframe_mapping[selected_tf_label]

current_cache_min = int(st.session_state.config.get("cache_ttl_minutes", 60))
selected_cache_min = st.sidebar.slider("⏱️ Cache in Min:", min_value=5, max_value=360, value=current_cache_min, step=5)

if (selected_chart_type != st.session_state.config["chart_type"] or
    selected_timeframe != st.session_state.config["timeframe"] or
    selected_cache_min != current_cache_min):
    st.session_state.config["chart_type"] = selected_chart_type
    st.session_state.config["timeframe"] = selected_timeframe
    st.session_state.config["cache_ttl_minutes"] = selected_cache_min
    save_config(st.session_state.config)
    st.rerun()

# --- INTELLIGENTE SUCHFUNKTION NACH NAME / TICKER ---
st.sidebar.divider()
st.sidebar.header(f"🔍 Aktie suchen & zu '{active_cat}' hinzufügen")

search_query = st.sidebar.text_input("Unternehmensname oder Ticker:", "").strip()

if search_query:
    try:
        search_obj = yf.Search(search_query)
        quotes = search_obj.quotes
        if quotes:
            options = {}
            for q in quotes:
                sym = q.get('symbol')
                name = q.get('shortname', q.get('longname', sym))
                exch = q.get('exchange', 'N/A')
                label = f"{name} ({sym}) [{exch}]"
                options[label] = sym

            selected_label = st.sidebar.selectbox("Suchergebnisse:", list(options.keys()))
            if st.sidebar.button("➕ Ausgewählte Aktie hinzufügen"):
                chosen_symbol = options[selected_label]
                if chosen_symbol not in current_tickers:
                    current_tickers.append(chosen_symbol)
                    save_config(st.session_state.config)
                    st.success(f"{chosen_symbol} hinzugefügt!")
                    st.rerun()
                else:
                    st.sidebar.warning("Aktie ist bereits in dieser Kategorie.")
        else:
            st.sidebar.info("Keine Ergebnisse gefunden.")
    except Exception:
        st.sidebar.error("Fehler bei der Suche.")

st.sidebar.divider()
selected_ticker = st.sidebar.selectbox("🔎 Detail-Analyse wählen:", current_tickers)

if st.sidebar.button(f"🗑️ {selected_ticker} löschen"):
    if len(current_tickers) > 1:
        current_tickers.remove(selected_ticker)
        save_config(st.session_state.config)
        st.rerun()
    else:
        st.sidebar.warning("Mindestens 1 Aktie muss bleiben.")


# --- DASHBOARD GRID (Übersicht) ---
st.subheader(f"Übersicht: {active_cat} ({len(current_tickers)} Aktien in EUR) | Zeitraum: {selected_tf_label}")

cols = st.columns(4)

for idx, ticker in enumerate(current_tickers):
    col = cols[idx % 4]
    with col:
        try:
            hist, info = load_stock_data(ticker, selected_timeframe)
            if not hist.empty and len(hist) > 0:
                last_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[0]
                pct_change = ((last_price - prev_price) / prev_price) * 100
                currency = info.get('currency', 'EUR')

                last_row = hist.iloc[-1]
                day_open = last_row.get('Open')
                if day_open and day_open > 0:
                    day_change = ((last_price - day_open) / day_open) * 100
                    day_change_str = f"{day_change:+.2f}%"
                else:
                    prev_close = info.get('previousClose')
                    if prev_close and prev_close > 0:
                        day_change = ((last_price - prev_close) / prev_close) * 100
                        day_change_str = f"{day_change:+.2f}%"
                    else:
                        day_change_str = "N/A"

                bh_score = calculate_buy_and_hold_score(info, hist)
                buffett_score = calculate_buffett_score(info, hist)
                pe_val = info.get('forwardPE') or info.get('trailingPE')
                pe_str = f"{pe_val:.1f}" if pe_val is not None else "N/A"

                orig_hint = f" ({info.get('original_currency')})" if 'original_currency' in info else ""

                col.metric(
                    label=f"{info.get('shortName', ticker)} ({ticker}){orig_hint}",
                    value=f"{last_price:.2f} {currency}",
                    delta=f"Zeitraum: {pct_change:+.2f}%"
                )

                bh_display = f"{bh_score}" if bh_score is not None else "N/A"
                col.caption(f"☀️ Heute: **{day_change_str}** | 🛡️ B&H: **{bh_display}** | 🎩 Buffett: **{buffett_score}** | KGV: **{pe_str}**")

                fig = go.Figure()
                if selected_chart_type == "Fläche (Area)":
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', fill='tozeroy', line=dict(color='green' if pct_change >= 0 else 'red', width=2)))
                elif selected_chart_type == "Candlestick":
                    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close']))
                else:
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', line=dict(color='green' if pct_change >= 0 else 'red', width=2)))

                fig.update_layout(
                    height=160,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(visible=True, showticklabels=True),
                    yaxis=dict(visible=True, showticklabels=True, side='right'),
                    showlegend=False
                )
                col.plotly_chart(fig, use_container_width=True)
            else:
                col.warning(f"Keine Kursdaten für {ticker}")
        except Exception:
            col.error(f"Fehler bei {ticker}")

st.divider()


# --- DETAIL-ANSICHT & SCORE-BERECHNUNG ---
if selected_ticker in current_tickers:
    st.subheader(f"🔍 Detail-Analyse & Scores: {selected_ticker}")

    hist, info = load_stock_data(selected_ticker, selected_timeframe)

    bh_details = calculate_buy_and_hold_details(info, hist)
    bh_score = bh_details["score"]
    quality_score = bh_details["quality_score"]
    valuation_score = bh_details["valuation_score"]

    buffett_score = calculate_buffett_score(info, hist)
    trade_score = calculate_trading_score(info, hist)

    if not hist.empty:
        last_price_det = hist['Close'].iloc[-1]
        last_row_det = hist.iloc[-1]
        day_open_det = last_row_det.get('Open')
        if day_open_det and day_open_det > 0:
            day_change_det = ((last_price_det - day_open_det) / day_open_det) * 100
            day_change_det_str = f"{day_change_det:+.2f}%"
        else:
            prev_close_det = info.get('previousClose')
            if prev_close_det and prev_close_det > 0:
                day_change_det = ((last_price_det - prev_close_det) / prev_close_det) * 100
                day_change_det_str = f"{day_change_det:+.2f}%"
            else:
                day_change_det_str = "N/A"
    else:
        day_change_det_str = "N/A"

    st.markdown(f"**Heutige Tagesperformance:** {day_change_det_str}")

    sc_col1, sc_col2, sc_col3, sc_col4, sc_col5 = st.columns(5)
    with sc_col1:
        st.metric(label="🛡️ B&H Gesamt", value=f"{bh_score if bh_score is not None else 'N/A'} / 100")
        if bh_score is not None: st.progress(bh_score / 100)
    with sc_col2:
        st.metric(label="⭐ B&H Qualität", value=f"{quality_score if quality_score is not None else 'N/A'} / 100")
        if quality_score is not None: st.progress(quality_score / 100)
    with sc_col3:
        st.metric(label="🏷️ B&H Bewertung", value=f"{valuation_score if valuation_score is not None else 'N/A'} / 100")
        if valuation_score is not None: st.progress(valuation_score / 100)
    with sc_col4:
        st.metric(label="🎩 Buffett Score", value=f"{buffett_score if buffett_score is not None else 'N/A'} / 100")
        if buffett_score is not None: st.progress(buffett_score / 100)
    with sc_col5:
        st.metric(label="📈 Trading Score", value=f"{trade_score if trade_score is not None else 'N/A'} / 100")
        if trade_score is not None: st.progress(trade_score / 100)

    # --- FUNDAMENTALDATEN-KURZBEWERTUNG (eigenes Modul) ---

    d_col1, d_col2 = st.columns([2, 1])

    with d_col1:
        currency = info.get('currency', 'EUR')
        st.markdown(f"### Kursverlauf in EUR (Echte EUR-Performance) ({selected_tf_label} - {selected_chart_type})")

        fig_detail = go.Figure()
        if not hist.empty:
            if selected_chart_type == "Fläche (Area)":
                fig_detail.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', fill='tozeroy', name=selected_ticker, line=dict(color='#1f77b4', width=2)))
            elif selected_chart_type == "Candlestick":
                fig_detail.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name=selected_ticker))
            else:
                fig_detail.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name=selected_ticker, line=dict(color='#1f77b4', width=2)))

        fig_detail.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_detail, use_container_width=True)

        if st.button(f"🔍 Erweiterte Chartanalyse für {selected_ticker} öffnen", use_container_width=True, key=f"btn_detail_chart_{selected_ticker}"):
            show_chart_analysis_dialog(selected_ticker, hist, info)

    with d_col2:
        st.markdown("### Wichtige Fundamentaldaten (in EUR)")

        raw_margin = info.get('profitMargins')
        profit_margin_str = f"{raw_margin * 100:.2f}%" if raw_margin is not None else 'N/A'

        dividend_rate = info.get('dividendRate')
        div_abs_str = f"{dividend_rate:.2f} {currency}" if dividend_rate is not None else '0.00 / Keine'

        last_close_price = hist['Close'].iloc[-1] if not hist.empty else None
        if dividend_rate and last_close_price and last_close_price > 0:
            div_yield_str = f"{(dividend_rate / last_close_price) * 100:.2f}%"
        else:
            raw_div = info.get('dividendYield')
            if raw_div is not None:
                div_yield_str = f"{raw_div:.2f}%" if raw_div > 1.0 else f"{raw_div * 100:.2f}%"
            else:
                div_yield_str = 'N/A'

        kbv = info.get('priceToBook')
        kbv_str = f"{kbv:.2f}" if kbv is not None else 'N/A'

        beta_val = info.get('beta', 'N/A')
        beta_str = f"{beta_val:.2f}" if isinstance(beta_val, (int, float)) else 'N/A'

        trailing_eps = info.get('trailingEps')
        trailing_eps_str = f"{trailing_eps:.2f} {currency}" if isinstance(trailing_eps, (int, float)) else 'N/A'

        forward_eps = info.get('forwardEps')
        forward_eps_str = f"{forward_eps:.2f} {currency}" if isinstance(forward_eps, (int, float)) else 'N/A'

        earnings_growth = info.get('earningsGrowth')
        earnings_growth_str = f"{earnings_growth * 100:.2f}%" if earnings_growth is not None else 'N/A'

        if 'original_currency' in info:
            st.info(f"💱 Umgerechnet von Original-Währung: **{info['original_currency']}**")

        st.write(f"**Sektor:** {info.get('sector', 'N/A')}")
        st.write(f"**Beta (Marktsensitivität):** {beta_str}")
        st.write(f"**EPS (Trailing):** {trailing_eps_str}")
        st.write(f"**EPS (Forward):** {forward_eps_str}")
        st.write(f"**KGV (Trailing P/E):** {info.get('trailingPE', 'N/A')}")
        st.write(f"**KGV (Forward P/E):** {info.get('forwardPE', 'N/A')}")
        st.write(f"**KBV (Price-to-Book):** {kbv_str}")
        st.write(f"**Erw. Gewinnwachstum:** {earnings_growth_str}")
        st.write(f"**Dividende (absolut):** {div_abs_str}")
        st.write(f"**Dividendenrendite:** {div_yield_str}")
        st.write(f"**Gewinnmarge:** {profit_margin_str}")
        st.write(f"**52-Wochen Hoch:** {info.get('fiftyTwoWeekHigh', 'N/A')} {currency}")
        st.write(f"**52-Wochen Tief:** {info.get('fiftyTwoWeekLow', 'N/A')} {currency}")

    # --- AUSKLABBARER ERKLÄRUNGS-CRASHKURS ZU DEN KENNZAHLEN ---
    st.markdown("---")
    show_fundamental_analysis(info)

    with st.expander("📚 Crashkurs: Was bedeuten diese Fundamentaldaten? (Nachschlagewerk)"):
        st.markdown("""
        * **Beta (Marktsensitivität):** Misst die Schwankung der Aktie im Vergleich zum Gesamtmarkt.
          * *Beta = 1:* Läuft wie der Markt.
          * *Beta > 1:* Schwankt stärker als der Markt (höheres Risiko/Chance).
          * *Beta < 1:* Verhält sich defensiver.
        * **EPS (Earnings Per Share / Gewinn pro Aktie):** Zeigt, wie viel Nettogewinn das Unternehmen je ausgegebener Aktie erwirtschaftet hat (*Trailing* = letztes Jahr, *Forward* = geschätzt für das kommende Jahr).
        * **KGV (Kurs-Gewinn-Verhältnis / P/E):** Setzt den Aktienkurs ins Verhältnis zum Gewinn. Ein niedrigeres KGV bedeutet oft, dass die Aktie günstiger bewertet ist, muss aber im Branchenvergleich betrachtet werden (*Trailing* = historisch, *Forward* = basierend auf Zukunftsgewinnen).
        * **KBV (Kurs-Buchwert-Verhältnis / Price-to-Book):** Vergleicht den Aktienkurs mit dem buchhalterischen Eigenkapital je Aktie. Werte unter 1 können auf eine Unterbewertung hindeuten.
        * **Erwartetes Gewinnwachstum:** Prognostiziertes prozentuales Gewinnwachstum des Unternehmens für die kommenden Jahre.
        * **Dividende & Dividendenrendite:** Der ausgeschüttete Gewinn pro Aktie im Verhältnis zum aktuellen Aktienkurs. Zeigt den passiven Cashflow, den du als Anleger erhältst.
        * **Gewinnmarge:** Zeigt, wie viel Prozent vom Umsatz am Ende als echter Gewinn beim Unternehmen hängen bleiben (hohe Margen sprechen für starke Preismacht).
        * **52-Wochen Hoch / Tief:** Die Höchst- und Tiefstkurse der letzten 12 Monate. Zeigt, wo sich die Aktie aktuell in ihrer Jahrespreisspanne befindet.
        """)
