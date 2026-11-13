from math import isfinite

import pandas as pd


def calculate_trading_score(info, hist):
    """
    Berechnet einen Trading-Score von 0 bis 100 anhand von Momentum,
    Volatilität und dem Abstand zum 52-Wochen-Hoch.

    Bei weniger als sechs gültigen Schlusskursen ist der Score neutral.
    """
    score = 50

    if hist is None or hist.empty or "Close" not in hist.columns:
        return score

    close = pd.to_numeric(hist["Close"], errors="coerce").sort_index()
    valid = close.gt(0) & close.lt(float("inf"))
    close = close.where(valid)
    valid_close = close.dropna()

    if len(valid_close) < 6:
        return score

    # 1. Momentum über den ausgewählten Zeitraum
    current_price = valid_close.iloc[-1]
    performance = (current_price / valid_close.iloc[0] - 1) * 100

    if performance > 15:
        score += 25
    elif performance > 5:
        score += 15
    elif performance < -10:
        score -= 20

    # 2. Volatilität zwischen aufeinanderfolgenden Kursbalken
    # Fehlende Kurse werden für die Renditeberechnung nicht überbrückt.
    returns = close.pct_change(fill_method=None)
    volatility = returns.std() * 100

    if isfinite(volatility):
        if volatility > 2.5:
            score += 20
        elif volatility < 1.0:
            score -= 10

    # 3. Nähe zum 52-Wochen-Hoch oder Ausbruch darüber
    try:
        high_52 = float((info or {}).get("fiftyTwoWeekHigh"))
    except (TypeError, ValueError, OverflowError):
        high_52 = 0.0

    if isfinite(high_52) and high_52 > 0:
        distance_pct = (high_52 - current_price) / high_52 * 100

        if current_price > high_52:
            score += 15  # Kurs über dem gemeldeten 52-Wochen-Hoch
        elif distance_pct < 3:
            score += 15  # Weniger als 3 % unter dem 52-Wochen-Hoch
        elif distance_pct > 30:
            score -= 10

    return max(0, min(100, score))
