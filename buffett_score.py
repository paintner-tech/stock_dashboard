def calculate_buffett_score(info, hist):
    """
    Warren-Buffett-Score (Ultra-Strikt): 
    Startet bei 40 Punkten. 100 Punkte erreichen nur absolute Value-Festungen.
    """
    score = 40  # Konservativer Startpunkt
    
    # 1. Burggraben & Preismacht (Gewinnmarge)
    margin = info.get('profitMargins')
    if margin is not None:
        if margin > 0.35:
            score += 25  # Monarchie-Status (unglaubliche Marge)
        elif margin > 0.20:
            score += 10  # Guter Burggraben
        elif 0 < margin <= 0.10:
            score -= 10  # Zu dünne Marge für einen echten Burggraben
        elif margin < 0:
            score -= 35  # Verlustgeschäft (No-Go)
        
    # 2. Kapitalrendite (ROE)
    roe = info.get('returnOnEquity')
    if roe is not None:
        if roe > 0.25:
            score += 20  # Elite-Effizienz
        elif roe > 0.15:
            score += 10  # Gut
        elif 0 <= roe <= 0.10:
            score -= 10  # Zu schwach
        elif roe < 0:
            score -= 25  # Kapitalvernichtung

    # 3. Bilanz & Schuldenfreiheit (Debt to Equity)
    debt_to_equity = info.get('debtToEquity')
    if debt_to_equity is not None:
        if debt_to_equity < 20:
            score += 15  # Nahezu schuldenfrei (Buffett-Traum)
        elif 20 <= debt_to_equity <= 60:
            score += 5   # Gesunde Bilanz
        elif 60 < debt_to_equity <= 120:
            score -= 10  # Zu viel Fremdkapital
        elif debt_to_equity > 120:
            score -= 30  # Gefährliche Schuldenlast

    # 4. Sicherheitsmarge beim KGV (Margin of Safety)
    pe = info.get('forwardPE') or info.get('trailingPE')
    if pe is not None:
        if pe < 0:
            score -= 30  # Negative Gewinne
        elif 0 < pe < 12:
            score += 20  # Klassisches Value-Schnäppchen
        elif 12 <= pe <= 18:
            score += 10  # Fairer Einstiegspreis
        elif 18 < pe <= 25:
            score -= 5   # Schon teuer
        elif 25 < pe <= 35:
            score -= 20  # Viel zu teuer für Value-Investing
        elif pe > 35:
            score -= 35  # Extreme Übertreibung

    # 5. Kurs-Buchwert-Verhältnis (KBV)
    pb = info.get('priceToBook')
    if pb is not None:
        if 0 < pb < 1.5:
            score += 10
        elif pb > 5.0:
            if margin and margin > 0.35:
                score -= 5   # Nur bei Monster-Margen milder
            else:
                score -= 20  # Viel zu teuer im Verhältnis zum Buchwert

    return max(0, min(100, score))
