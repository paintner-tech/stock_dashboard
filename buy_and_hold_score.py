"""Buy-&-Hold-Score aus Unternehmensqualität und Bewertung."""

import json
from math import isfinite
from pathlib import Path


# Der Pfad richtet sich nach dem Speicherort des Moduls. Dadurch wird beim
# Start aus einem anderen Arbeitsverzeichnis dieselbe Konfiguration geladen.
CONFIG_FILE = Path(__file__).parent / "config" / "buy_and_hold_score.json"
QUALITY_KEYS = ("profitMargins", "returnOnEquity", "debtToEquity")
VALUATION_KEYS = ("pe", "priceToBook")


def _number(value):
    """Wandelt eine Zahl oder einen Zahlenstring in eine endliche Zahl um."""
    # Python behandelt True und False auch als 1 und 0. In den Kurs- und
    # Fundamentaldaten sind sie für diese Kennzahlen aber ungültig.
    if value is None or isinstance(value, bool):
        return None

    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    return value if isfinite(value) else None


def _config_number(config, section, key, *, integer=False):
    """Prüft Zahlen aus JSON. Zahlenstrings und Wahrheitswerte sind ungültig."""
    value = config[section][key]
    if integer:
        if type(value) is not int:
            raise ValueError(f"{section}.{key} muss eine ganze Zahl sein.")
        return value

    number = _number(value) if type(value) in (int, float) else None
    if number is None:
        raise ValueError(f"{section}.{key} muss eine endliche Zahl sein.")
    return number


def _read_anchors(config, key):
    """Liest die Paare [Kennzahlwert, Punkte] für eine einzelne Kennzahl."""
    pairs = config["stuetzpunkte"][key]
    error = (
        f"stuetzpunkte.{key} braucht mindestens zwei Paare [Kennzahlwert, Punkte] "
        "mit aufsteigenden Kennzahlwerten und Punkten zwischen 0 und 100."
    )
    if not isinstance(pairs, list) or len(pairs) < 2:
        raise ValueError(error)

    anchors = []
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(error)
        value, points = (_number(item) if type(item) in (int, float) else None for item in pair)
        if value is None or points is None or not 0 <= points <= 100:
            raise ValueError(error)
        # Gleiche Kennzahlwerte würden bei der Interpolation durch 0 teilen.
        if anchors and value <= anchors[-1][0]:
            raise ValueError(error)
        anchors.append((value, points))
    return tuple(anchors)


def _load_config():
    """Lädt und prüft die JSON-Einstellungen beim Start des Dashboards."""
    try:
        with CONFIG_FILE.open(encoding="utf-8") as config_file:
            config = json.load(config_file)

        # Wir lesen nur die bekannten Einstellungen. So können Erklärungstexte
        # unter _hinweise in der JSON-Datei stehen und werden ignoriert.
        quality_percent = _config_number(config, "gesamt", "qualitaet_prozent", integer=True)
        valuation_percent = _config_number(config, "gesamt", "bewertung_prozent", integer=True)
        start_value = _config_number(config, "gesamt", "startwert")
        minimum_quality_metrics = _config_number(
            config, "qualitaet", "mindestanzahl_kennzahlen", integer=True
        )
        cap_threshold = _config_number(config, "qualitaet", "deckel_schwelle")
        cap_maximum = _config_number(config, "qualitaet", "deckel_maximum")

        if min(quality_percent, valuation_percent) <= 0 or quality_percent + valuation_percent != 100:
            raise ValueError("Die beiden Anteile in gesamt müssen positiv sein und zusammen 100 ergeben.")
        if not 1 <= minimum_quality_metrics <= len(QUALITY_KEYS):
            raise ValueError("qualitaet.mindestanzahl_kennzahlen muss zwischen 1 und 3 liegen.")
        if not (0 <= cap_threshold <= 100 and 0 <= cap_maximum <= 100):
            raise ValueError("Schwelle und Maximum des Qualitätsdeckels müssen zwischen 0 und 100 liegen.")

        quality_weights = {
            key: _config_number(config, "gewichte_qualitaet", key) for key in QUALITY_KEYS
        }
        valuation_weights = {
            key: _config_number(config, "gewichte_bewertung", key) for key in VALUATION_KEYS
        }
        for key, weight in {**quality_weights, **valuation_weights}.items():
            if weight <= 0:
                raise ValueError(f"Das Gewicht für {key} muss positiv sein.")

        return {
            "quality_share": quality_percent / 100,
            "valuation_share": valuation_percent / 100,
            "start_value": start_value,
            "minimum_quality_metrics": minimum_quality_metrics,
            "cap_threshold": cap_threshold,
            "cap_maximum": cap_maximum,
            "quality_weights": quality_weights,
            "valuation_weights": valuation_weights,
            "anchors": {key: _read_anchors(config, key) for key in QUALITY_KEYS + VALUATION_KEYS},
        }
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Fehler in der Score-Konfiguration {CONFIG_FILE}: {exc}") from exc


SETTINGS = _load_config()


def _interpolate(value, anchors):
    """Rechnet eine Kennzahl anhand der eingestellten Stützpunkte in Punkte um."""
    if value <= anchors[0][0]:
        return anchors[0][1]

    for (left, left_points), (right, right_points) in zip(anchors, anchors[1:]):
        if value <= right:
            # Beispiel KGV 20: Zwischen 16 und 24 liegt es bei 50 % der Strecke.
            # Von 75 auf 40 Punkte geht es damit ebenfalls die halbe Strecke.
            fraction = (value - left) / (right - left)
            return left_points + fraction * (right_points - left_points)

    return anchors[-1][1]


def _weighted_average(points, weights):
    """Berechnet den Teilwert aus den vorhandenen Kennzahlen und ihren Gewichten."""
    total_points = 0
    total_weight = 0

    for key, weight in weights.items():
        if points[key] is not None:
            # Eine Kennzahl mit 0 Punkten fließt ein. Eine fehlende Kennzahl
            # (None) lässt ihr Gewicht frei, sodass der Rest stärker zählt.
            total_points += points[key] * weight
            total_weight += weight

    return total_points / total_weight if total_weight else None


def _select_pe(info):
    """Ermittelt KGV, Quelle und gegebenenfalls einen Hinweis auf Verluste."""
    # Zuerst prüfen wir das erwartete KGV. Ist dazu weder ein brauchbares KGV
    # noch ein Verlustsignal vorhanden, prüfen wir die rückblickenden Zahlen.
    for source, pe_key, eps_key in (
        ("Forward", "forwardPE", "forwardEps"),
        ("Trailing", "trailingPE", "trailingEps"),
    ):
        pe = _number(info.get(pe_key))
        eps = _number(info.get(eps_key))

        # Ein negatives Ergebnis je Aktie (EPS) genügt als Verlustsignal.
        # Deshalb greift diese Regel auch, wenn der Anbieter kein KGV meldet.
        if (pe is not None and pe < 0) or (eps is not None and eps < 0):
            note = "Erwartete Verluste" if source == "Forward" else "Verluste im Rückblick"
            return pe if pe is not None and pe < 0 else None, source, note

        if pe is not None and pe > 0:
            return pe, source, None

    return None, None, None


def calculate_buy_and_hold_details(info, hist=None):
    """Liefert Gesamtwert, Teilwerte und Datengrundlage für das Dashboard."""
    # hist ist für bestehende Aufrufe weiterhin erlaubt. Dieser Score verwendet
    # nur die Fundamentaldaten in info, also keinen historischen Kursverlauf.
    margin = _number(info.get("profitMargins"))
    roe = _number(info.get("returnOnEquity"))
    debt_to_equity = _number(info.get("debtToEquity"))
    book_value = _number(info.get("bookValue"))
    price_to_book = _number(info.get("priceToBook"))
    pe, pe_source, pe_note = _select_pe(info)
    anchors = SETTINGS["anchors"]

    # 1. Jede brauchbare Kennzahl wird auf die Skala von 0 bis 100 gebracht.
    # Marge und Eigenkapitalrendite sind Dezimalwerte. 0.15 entspricht 15 %.
    margin_points = None
    if margin is not None:
        margin_points = _interpolate(margin, anchors["profitMargins"])

    roe_points = None
    if roe is not None:
        roe_points = _interpolate(roe, anchors["returnOnEquity"])

    # Debt/Equity kommt in Prozentpunkten. Der Rohwert 40 bedeutet 40 %.
    debt_points = None
    if book_value is not None and book_value < 0:
        debt_points = 0
        # Bei negativem Eigenkapital kann ein positiver ROE durch zwei negative
        # Werte entstehen. In diesem Fall lassen wir den ROE aus der Wertung.
        roe_points = None
    elif debt_to_equity is not None and debt_to_equity >= 0:
        debt_points = _interpolate(debt_to_equity, anchors["debtToEquity"])

    pe_points = None
    if pe_note is not None:
        pe_points = 0
    elif pe is not None:
        pe_points = _interpolate(pe, anchors["pe"])

    pb_points = None
    if price_to_book is not None and price_to_book > 0:
        pb_points = _interpolate(price_to_book, anchors["priceToBook"])

    points = {
        "profitMargins": margin_points,
        "returnOnEquity": roe_points,
        "debtToEquity": debt_points,
        "pe": pe_points,
        "priceToBook": pb_points,
    }

    # 2. Qualität braucht genügend Kennzahlen. Bei den Standardgewichten
    # zählen mit vollständigen Daten Marge, ROE und Verschuldung wie 25:15:20.
    quality_count = sum(points[key] is not None for key in QUALITY_KEYS)
    quality_score = None
    if quality_count >= SETTINGS["minimum_quality_metrics"]:
        quality_score = _weighted_average(points, SETTINGS["quality_weights"])

    # 3. Die Bewertung braucht ein KGV oder ein erkanntes Verlustsignal.
    # Ohne KBV zählt das KGV allein. Ein Verlustsignal setzt den ganzen
    # Bewertungsteil auf 0, selbst bei einem niedrigen Kurs-Buchwert-Verhältnis.
    valuation_score = None
    if pe_points is not None:
        valuation_score = (
            0 if pe_note is not None else _weighted_average(points, SETTINGS["valuation_weights"])
        )

    # 4. Nur mit beiden Teilwerten gibt es einen Gesamtscore. Beispiel mit den
    # Standardanteilen: 70 Qualität und 50 Bewertung ergeben 0.60 * 70 +
    # 0.40 * 50 = 62 Punkte. Danach kommen Startwert und gegebenenfalls Deckel.
    score = None
    if quality_score is not None and valuation_score is not None:
        score = (
            SETTINGS["quality_share"] * quality_score
            + SETTINGS["valuation_share"] * valuation_score
            + SETTINGS["start_value"]
        )
        # Der Deckel verhindert, dass eine günstige Bewertung schwache Qualität
        # zu stark ausgleicht. Die Qualitätsprüfung verwendet den Rohwert.
        if quality_score < SETTINGS["cap_threshold"]:
            score = min(score, SETTINGS["cap_maximum"])
        score = max(0, min(score, 100))

    # Erst für die Rückgabe runden. So beeinflussen gerundete Teilwerte weder
    # den Gesamtscore noch die Entscheidung über den Qualitätsdeckel.
    return {
        "score": round(score) if score is not None else None,
        "quality_score": round(quality_score) if quality_score is not None else None,
        "valuation_score": round(valuation_score) if valuation_score is not None else None,
        "available_metrics": sum(value is not None for value in points.values()),
        "total_metrics": len(points),
        "pe": pe,
        "pe_source": pe_source,
        "pe_note": pe_note,
    }


def calculate_buy_and_hold_score(info, hist=None):
    """Liefert nur den Gesamtwert für bestehende Aufrufe."""
    return calculate_buy_and_hold_details(info, hist)["score"]
