"""
Fundamentalanalyse für das Aktien-Dashboard.

Die Funktion bewertet ausgewählte Fundamentaldaten qualitativ und erzeugt
eine kurze, nachvollziehbare Zusammenfassung. Es wird bewusst kein weiterer
Gesamtscore berechnet.

Grenzwerte können zentral in FUNDAMENTAL_THRESHOLDS angepasst werden.
Die Werte sind allgemeine Orientierungswerte und müssen je nach Branche
(z. B. Banken, Versicherungen, REITs, Versorger) anders interpretiert werden.
"""

import math
import json
from pathlib import Path
import streamlit as st


# Standard-Richtwerte. Sie werden bei Bedarf nach ~/config/fundamental_analysis.json
# geschrieben und können dort dauerhaft angepasst werden.
DEFAULT_FUNDAMENTAL_THRESHOLDS = {
    "profit_margin_strong": 0.15,
    "profit_margin_weak": 0.05,
    "revenue_growth_good": 0.08,
    "revenue_growth_weak": 0.00,
    "earnings_growth_good": 0.10,
    "earnings_growth_weak": 0.00,
    "roe_good": 0.15,
    "roe_weak": 0.05,
    "debt_to_equity_high": 150.0,
    "current_ratio_good": 1.5,
    "current_ratio_weak": 1.0,
    "pe_low": 15.0,
    "pe_high": 30.0,
    "dividend_yield_attractive": 0.04,
    "payout_ratio_high": 0.80,
}

CONFIG_DIR = Path.home() / "config"
FUNDAMENTAL_CONFIG_FILE = CONFIG_DIR / "fundamental_analysis.json"


def load_fundamental_thresholds():
    """Lädt Grenzwerte aus ~/config oder legt die Standarddatei an."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if FUNDAMENTAL_CONFIG_FILE.exists():
        try:
            with FUNDAMENTAL_CONFIG_FILE.open("r", encoding="utf-8") as file:
                stored = json.load(file)
            if isinstance(stored, dict):
                # Neue Grenzwerte ergänzen, falls die Datei älter/unvollständig ist.
                thresholds = dict(DEFAULT_FUNDAMENTAL_THRESHOLDS)
                thresholds.update({
                    key: value for key, value in stored.items()
                    if key in DEFAULT_FUNDAMENTAL_THRESHOLDS
                    and isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                })
                return thresholds
        except (OSError, json.JSONDecodeError):
            pass

    thresholds = dict(DEFAULT_FUNDAMENTAL_THRESHOLDS)
    try:
        with FUNDAMENTAL_CONFIG_FILE.open("w", encoding="utf-8") as file:
            json.dump(thresholds, file, indent=4, ensure_ascii=False)
    except OSError:
        # Die Analyse läuft mit Standardwerten weiter, falls das Verzeichnis
        # beispielsweise nicht beschreibbar ist.
        pass
    return thresholds


FUNDAMENTAL_THRESHOLDS = load_fundamental_thresholds()


def _number(info, key):
    """Liefert nur endliche numerische Werte; sonst None."""
    value = info.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _pct(value):
    return f"{value * 100:.1f}%"


def _metric_line(label, value, interpretation):
    if value is None:
        return f"**{label}:** Keine verlässlichen Daten verfügbar."
    return f"**{label}:** {value} – {interpretation}"


def analyze_fundamentals(info, thresholds=None):
    """
    Erstellt eine strukturierte Fundamentaldaten-Auswertung.

    Rückgabe:
        dict mit summary, sections, positives, warnings und data_quality.
    """
    info = info or {}
    t = dict(FUNDAMENTAL_THRESHOLDS)
    if thresholds:
        t.update(thresholds)

    margin = _number(info, "profitMargins")
    revenue_growth = _number(info, "revenueGrowth")
    earnings_growth = _number(info, "earningsGrowth")
    roe = _number(info, "returnOnEquity")
    debt_to_equity = _number(info, "debtToEquity")
    current_ratio = _number(info, "currentRatio")
    trailing_pe = _number(info, "trailingPE")
    forward_pe = _number(info, "forwardPE")
    dividend_yield = _number(info, "dividendYield")
    st.write("DEBUG dividendYield:", info.get("dividendYield"))
    st.write("DEBUG nach _number:", dividend_yield)
    payout_ratio = _number(info, "payoutRatio")
    free_cashflow = _number(info, "freeCashflow")

    positives, warnings, sections = [], [], []

    # Profitabilität
    if margin is not None:
        if margin >= t["profit_margin_strong"]:
            positives.append(f"Hohe Nettogewinnmarge von {_pct(margin)}.")
            margin_text = "starke Profitabilität"
        elif margin < t["profit_margin_weak"]:
            warnings.append(f"Niedrige Nettogewinnmarge von {_pct(margin)}.")
            margin_text = "eher geringe Profitabilität"
        else:
            margin_text = "mittlere Profitabilität"
    else:
        margin_text = "mangels Daten nicht beurteilbar"

    if roe is not None:
        if roe >= t["roe_good"]:
            positives.append(f"Die Eigenkapitalrendite ist mit {_pct(roe)} hoch.")
            roe_text = "hohe Kapitalrendite"
        elif roe < t["roe_weak"]:
            warnings.append(f"Die Eigenkapitalrendite ist mit {_pct(roe)} niedrig.")
            roe_text = "niedrige Kapitalrendite"
        else:
            roe_text = "moderate Kapitalrendite"
    else:
        roe_text = "keine ausreichenden Daten"

    sections.append({
        "title": "Profitabilität",
        "items": [
            _metric_line("Nettogewinnmarge", _pct(margin) if margin is not None else None, margin_text),
            _metric_line("Eigenkapitalrendite (ROE)", _pct(roe) if roe is not None else None, roe_text),
        ],
    })

    # Wachstum
    growth_texts = []
    if revenue_growth is not None:
        if revenue_growth >= t["revenue_growth_good"]:
            positives.append(f"Der Umsatz wächst um {_pct(revenue_growth)}.")
            growth_texts.append("positives Umsatzwachstum")
        elif revenue_growth < t["revenue_growth_weak"]:
            warnings.append(f"Der Umsatz ist rückläufig ({_pct(revenue_growth)}).")
            growth_texts.append("rückläufiger Umsatz")
        else:
            growth_texts.append("schwaches Umsatzwachstum")

    if earnings_growth is not None:
        if earnings_growth >= t["earnings_growth_good"]:
            positives.append(f"Das Gewinnwachstum liegt bei {_pct(earnings_growth)}.")
            growth_texts.append("starkes Gewinnwachstum")
        elif earnings_growth < t["earnings_growth_weak"]:
            warnings.append(f"Das Gewinnwachstum ist negativ ({_pct(earnings_growth)}).")
            growth_texts.append("rückläufiger Gewinn")
        else:
            growth_texts.append("moderates Gewinnwachstum")

    sections.append({
        "title": "Wachstum",
        "items": [
            _metric_line("Umsatzwachstum", _pct(revenue_growth) if revenue_growth is not None else None,
                         next((x for x in growth_texts if "Umsatz" in x), "nicht beurteilbar")),
            _metric_line("Gewinnwachstum", _pct(earnings_growth) if earnings_growth is not None else None,
                         next((x for x in growth_texts if "Gewinn" in x), "nicht beurteilbar")),
        ],
    })

    # Verschuldung und Liquidität
    if debt_to_equity is not None:
        if debt_to_equity >= t["debt_to_equity_high"]:
            warnings.append(f"Das Verhältnis von Schulden zu Eigenkapital ist erhöht ({debt_to_equity:.0f}%).")
            debt_text = "erhöhte Verschuldung; Branche beachten"
        else:
            debt_text = "kein auffälliger Wert nach allgemeinem Richtwert"
    else:
        debt_text = "nicht verfügbar"

    if current_ratio is not None:
        if current_ratio >= t["current_ratio_good"]:
            positives.append(f"Die kurzfristige Liquidität wirkt solide (Current Ratio {current_ratio:.2f}).")
            liquidity_text = "solider kurzfristiger Liquiditätspuffer"
        elif current_ratio < t["current_ratio_weak"]:
            warnings.append(f"Die Current Ratio liegt unter 1 ({current_ratio:.2f}).")
            liquidity_text = "kurzfristige Verbindlichkeiten nicht vollständig durch Umlaufvermögen gedeckt"
        else:
            liquidity_text = "knapper bis ausreichender Liquiditätspuffer"
    else:
        liquidity_text = "nicht verfügbar"

    sections.append({
        "title": "Finanzielle Stabilität",
        "items": [
            _metric_line("Debt-to-Equity", f"{debt_to_equity:.1f}%" if debt_to_equity is not None else None, debt_text),
            _metric_line("Current Ratio", f"{current_ratio:.2f}" if current_ratio is not None else None, liquidity_text),
            _metric_line("Free Cashflow", "positiv" if free_cashflow is not None and free_cashflow > 0 else
                         "negativ" if free_cashflow is not None and free_cashflow < 0 else
                         "nahe null" if free_cashflow == 0 else None,
                         "positiver Cashflow ist grundsätzlich vorteilhaft" if free_cashflow is not None and free_cashflow > 0
                         else "negativer Cashflow sollte geprüft werden" if free_cashflow is not None and free_cashflow < 0
                         else "nicht beurteilbar"),
        ],
    })
    if free_cashflow is not None and free_cashflow < 0:
        warnings.append("Der ausgewiesene Free Cashflow ist negativ.")

    # Bewertung
    pe_value = forward_pe if forward_pe is not None and forward_pe > 0 else trailing_pe
    pe_label = "Forward-KGV" if pe_value == forward_pe and pe_value is not None else "Trailing-KGV"
    if pe_value is not None and pe_value > 0:
        if pe_value < t["pe_low"]:
            valuation_text = "niedriges KGV; allein noch kein Beweis für eine Unterbewertung"
        elif pe_value > t["pe_high"]:
            valuation_text = "hohes KGV; die Bewertung setzt entsprechende Erwartungen voraus"
            warnings.append(f"Das {pe_label} ist mit {pe_value:.1f} relativ hoch.")
        else:
            valuation_text = "mittleres KGV; Branchenvergleich ist wichtig"
    else:
        valuation_text = "nicht sinnvoll beurteilbar (z. B. negativer oder fehlender Gewinn)"

    sections.append({
        "title": "Bewertung",
        "items": [
            _metric_line(pe_label, f"{pe_value:.1f}" if pe_value is not None and pe_value > 0 else None, valuation_text),
            _metric_line("PEG-Ratio", f"{_number(info, 'pegRatio'):.2f}" if _number(info, "pegRatio") is not None else None,
                         "setzt KGV und erwartetes Wachstum ins Verhältnis; nur bei brauchbaren Wachstumsdaten sinnvoll"),
        ],
    })

    # Dividende
    # Dividende
    if dividend_yield is not None:
        # Wenn der Wert als Prozentangabe vorliegt (z.B. 0.3 für 0.3% oder 3.5 für 3.5%),
        # teilen wir durch 100, um auf den Dezimalbruch zu kommen.
        # 0.20 (20%) dient hier als Grenze, da normale Dividendenrenditen als Dezimalbruch
        # praktisch nie über 0.20 liegen.
        if dividend_yield > 0.20:
            dividend_yield = dividend_yield / 100

        if dividend_yield >= t["dividend_yield_attractive"]:
            positives.append(f"Die Dividendenrendite ist mit {_pct(dividend_yield)} vergleichsweise hoch.")
            dividend_text = "attraktive laufende Rendite; Nachhaltigkeit prüfen"
        elif dividend_yield > 0:
            dividend_text = "vorhandene, aber eher moderate Dividendenrendite"
        else:
            dividend_text = "aktuell keine Dividendenrendite"
    else:
        dividend_text = "keine verlässlichen Daten"

    if payout_ratio is not None and payout_ratio > t["payout_ratio_high"]:
        warnings.append(f"Die Ausschüttungsquote ist mit {_pct(payout_ratio)} hoch; die Dividende könnte weniger Spielraum haben.")

    sections.append({
        "title": "Dividende",
        "items": [
            _metric_line("Dividendenrendite", _pct(dividend_yield) if dividend_yield is not None else None, dividend_text),
            _metric_line("Ausschüttungsquote", _pct(payout_ratio) if payout_ratio is not None else None,
                         "hohe Quote kann die finanzielle Flexibilität einschränken" if payout_ratio is not None and payout_ratio > t["payout_ratio_high"]
                         else "im allgemeinen Rahmen" if payout_ratio is not None else "nicht verfügbar"),
        ],
    })

    # Gesamttext: bewusst kein Kauf-/Verkaufssignal
    evaluated = sum(v is not None for v in [
        margin, revenue_growth, earnings_growth, roe, debt_to_equity,
        current_ratio, trailing_pe, forward_pe, dividend_yield, payout_ratio, free_cashflow
    ])
    if evaluated < 3:
        summary = "Die Datenlage ist zu dünn für eine belastbare fundamentale Einschätzung. Fehlende Kennzahlen sollten nicht als negative Unternehmensmerkmale gewertet werden."
    elif warnings and positives:
        summary = "Das Fundamentaldatenbild ist gemischt: Es gibt erkennbare Stärken, aber auch Punkte, die genauer geprüft werden sollten."
    elif warnings:
        summary = "Die verfügbaren Kennzahlen zeigen mehrere Auffälligkeiten. Vor einer positiven Einschätzung sollten deren Ursachen geprüft werden."
    elif positives:
        summary = "Die verfügbaren Kennzahlen wirken überwiegend solide. Das ist ein positives Qualitätsindiz, ersetzt aber weder Branchenvergleich noch Prüfung der Bewertung."
    else:
        summary = "Aus den verfügbaren Kennzahlen lässt sich derzeit keine klare Tendenz ableiten."

    return {
        "summary": summary,
        "sections": sections,
        "positives": positives,
        "warnings": warnings,
        "data_points": evaluated,
    }


def show_fundamental_analysis(info, thresholds=None):
    """Zeigt die Auswertung direkt in Streamlit an."""
    result = analyze_fundamentals(info, thresholds)

    st.markdown("### 🧾 Fundamentaldaten – Kurzbewertung")
    st.info(result["summary"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Stärken**")
        if result["positives"]:
            for item in result["positives"]:
                st.markdown(f"- ✅ {item}")
        else:
            st.caption("Keine eindeutigen Stärken aus den verfügbaren Daten ableitbar.")

    with col2:
        st.markdown("**Auffälligkeiten / Prüfpunkte**")
        if result["warnings"]:
            for item in result["warnings"]:
                st.markdown(f"- ⚠️ {item}")
        else:
            st.caption("Keine auffälligen Werte nach den verwendeten allgemeinen Richtwerten erkannt.")

    with st.expander("Kennzahlen und Einzelbewertung anzeigen", expanded=False):
        for section in result["sections"]:
            st.markdown(f"**{section['title']}**")
            for item in section["items"]:
                st.markdown(f"- {item}")
            st.markdown("")

        st.caption(
            f"Ausgewertete Kennzahlen: {result['data_points']}. "
            "Die Richtwerte sind allgemeine Orientierungshilfen, keine branchenübergreifend gültigen Regeln. "
            "Die Analyse ist keine Kauf- oder Verkaufsempfehlung."
        )

    return result
