# 📚 Projektdokumentation & Glossar

Willkommen in der Dokumentation des **Aktien-Dashboards**! Diese Seite dient als Nachschlagewerk für technische Begriffe, Berechnungsformeln, Indikatoren und methodische Hintergründe, die im Projekt verwendet werden.

---

## 📈 1. Technische Chartanalyse

### Unterstützungen (Support) & Widerstände
* **Definition:** Eine *Unterstützung* ist eine Preisregion, in der die Aktie in der Vergangenheit verlässlich Käufer gefunden hat. Ein *Widerstand* ist eine Region, an der sie auf Verkaufsdruck gestoßen ist.
* **Berechnung (Robuste Quantile):** 
  Um zu verhindern, dass einzelne Crash-Tage oder extreme Ausreißer die Linien verzerren, werden die Linien aus den letzten **90 Kerzen** des gewählten Zeitraums über statistische Quantile berechnet:
  * **Support:** Das 5 %-Quantil (`quantile(0.05)`) der Tiefstkurse. Die extremsten 5 % der Ausreißer nach unten werden ignoriert.
  * **Widerstand:** Das 95 %-Quantil (`quantile(0.95)`) der Höchstkurse.

### RSI (Relative Strength Index)
* Misst die Geschwindigkeit und Veränderung von Kursbewegungen auf einer Skala von 0 bis 100 (nach J. Welles Wilder, meist über 14 Perioden).
* **Überkauft (> 70):** Kurzfristig erhöhte Rücksetzergefahr.
* **Überverkauft (< 30):** Eine technische Gegenbewegung könnte bevorstehen.

### Gleitende Durchschnitte (SMA 50 / SMA 200)
* Zeigen den durchschnittlichen Schlusskurs über einen definierten Zeitraum (50 oder 200 Perioden). Dienen zur Bestimmung des Übergeordneten Trends (Kurs über SMA = positiv).

---

## 🧾 1.1 Fundamentaldaten & Kennzahlen

### Eigenkapitalrendite (ROE - Return on Equity)
* **Formel:** {Nettogewinn} / {Eigenkapital}
* **Hinweis:** Bei kapitalleichten Technologiegiganten (wie Apple) können massive Aktienrückkäufe das Eigenkapital stark verringern, wodurch die Eigenkapitalrendite mathematisch extrem steigen (teilweise > 100 %) kann. Dies zeigt eine hohe Kapitaleffizienz, sollte aber immer im Kontext von Verschuldung und Cashflow betrachtet werden.

---

## 🧮 1.2 Mathematische Grundlagen & Statistik

### Was ist ein Quantil?
Ein Quantil ist ein statistischer Trennwert, der eine sortierte Reihe von Daten in Teile teilt. 
* *Beispiel (5 %-Quantil):* Der Wert, unter dem genau 5 % aller Datenpunkte liegen (95 % sind höher). Das hilft in der Finanzanalyse, extreme statistische Ausreißer von echten Trendzonen zu trennen.

---
*Hinweis: Diese Dokumentation wird fortlaufend ergänzt.*

### 1.3 Bollinger Bänder

Die Bollinger Bänder sind ein technischer Indikator zur Analyse von Kursbewegungen und Volatilität. Sie zeigen, wie weit sich der aktuelle Aktienkurs von seinem gleitenden Durchschnitt entfernt hat und wie stark die Kursschwankungen momentan sind.

Die Bollinger Bänder bestehen aus drei Linien:

- **Mittleres Band:** Einfacher gleitender Durchschnitt (SMA) der letzten 20 Schlusskurse.
- **Oberes Band:** SMA 20 plus zwei Standardabweichungen.
- **Unteres Band:** SMA 20 minus zwei Standardabweichungen.

#### Berechnung

Das Dashboard verwendet die klassische Berechnung der Bollinger Bänder mit einem Zeitraum von 20 Perioden und einem Faktor von 2.

```python
# Mittleres Band: SMA 20
df["BB_Middle"] = df["Close"].rolling(
    window=20
).mean()

# Standardabweichung der letzten 20 Schlusskurse
std = df["Close"].rolling(
    window=20
).std()

# Oberes und unteres Band
df["BB_Upper"] = df["BB_Middle"] + (std * 2)
df["BB_Lower"] = df["BB_Middle"] - (std * 2)
```

Die Standardabweichung wird mit der Pandas-Standardmethode berechnet (Stichproben-Standardabweichung).

#### Interpretation

- **Kurs am unteren Band:** Der Kurs befindet sich relativ weit unterhalb seines Durchschnitts. Eine mögliche technische Gegenbewegung kann beobachtet werden.
- **Kurs am oberen Band:** Der Kurs befindet sich relativ weit oberhalb seines Durchschnitts. Eine mögliche kurzfristige Überdehnung kann vorliegen.
- **Enge Bänder:** Die Volatilität ist gering. Eine Phase niedriger Schwankungsbreite kann einer stärkeren Kursbewegung vorausgehen.
- **Weite Bänder:** Die Volatilität ist hoch und die Kursschwankungen sind ausgeprägter.

#### Wichtige Hinweise

Ein Berühren oder Überschreiten der Bollinger Bänder ist kein automatisches Kauf- oder Verkaufssignal.

In starken Aufwärts- oder Abwärtstrends kann sich der Kurs über längere Zeit entlang eines äußeren Bandes bewegen. Die Bänder sollten deshalb immer zusammen mit anderen Indikatoren wie RSI, SMA 50 und SMA 200 betrachtet werden.

Die Bollinger Bänder dienen ausschließlich der technischen Analyse und stellen keine eigenständige Anlageentscheidung dar.

## ⭐ 2. So funktionieren die Scores

Das Dashboard zeigt drei Scores von **0 bis 100 Punkten**. Der Buy-&-Hold-Score trennt Unternehmensqualität und Aktienbewertung. Der Buffett-Score prüft ausgewählte Fundamentalkennzahlen anhand fester Schwellen. Der Trading-Score bewertet den Kursverlauf.

### 2.1 Buy-&-Hold-Score

Der Buy-&-Hold-Score bewertet Aktien aus Sicht einer langfristigen Anlage. Er setzt sich zu **60 % aus Unternehmensqualität** und zu **40 % aus Aktienbewertung** zusammen.

| Bereich | Kennzahl | Gewicht im Gesamtscore | Was bringt mehr Punkte? |
| --- | --- | ---: | --- |
| Qualität | Nettomarge | 25 % | Höhere Marge |
| Qualität | Eigenkapitalrendite (ROE) | 15 % | Höhere Rendite |
| Qualität | Verschuldung im Verhältnis zum Eigenkapital | 20 % | Geringere Verschuldung |
| Bewertung | Kurs-Gewinn-Verhältnis (KGV) | 30 % | Niedrigeres positives KGV |
| Bewertung | Kurs-Buchwert-Verhältnis (KBV) | 10 % | Niedrigeres positives KBV |

Jede Kennzahl erhält anhand festgelegter Stützpunkte einen Wert von 0 bis 100. Dazwischen wird linear interpoliert. Eine Nettomarge von 15 % ergibt zum Beispiel 65 Punkte für diese Kennzahl, eine Marge von 30 % ergibt 100 Punkte.

Die Bewertung verwendet bevorzugt das erwartete KGV (Forward-KGV) und greift bei Bedarf auf das historische KGV (Trailing-KGV) zurück. Fehlt das KBV, zählt das KGV innerhalb der Bewertung allein. Die Qualität erfordert mindestens zwei auswertbare Kennzahlen. Fehlt einer der beiden Teilwerte, entfällt der Gesamtscore. Liegt die Qualität unter 40 Punkten, ist der Gesamtscore auf höchstens 59 Punkte begrenzt.

### 2.2 Buffett-Score

Der Buffett-Score startet bei **40 Punkten**. Je nach Schwellenwerten für Nettomarge, Eigenkapitalrendite, Verschuldung, KGV und KBV kommen Punkte hinzu oder werden abgezogen.

Die Kennzahlen dienen als Anhaltspunkte für ein profitables, solide finanziertes Unternehmen zu einem angemessenen Preis. Ob das Unternehmen einen dauerhaften Wettbewerbsvorteil hat, lässt sich aus diesen Kennzahlen allein nicht ableiten.

### 2.3 Trading-Score

Der Trading-Score startet bei **50 Punkten**. Er bewertet das Momentum im ausgewählten Zeitraum, die Schwankungen zwischen aufeinanderfolgenden Kursbalken und die Nähe zum 52-Wochen-Hoch.

| Kriterium | Bedingung | Punkte |
| --- | --- | ---: |
| Momentum | Kursgewinn über 15 % | +25 |
| Momentum | Kursgewinn über 5 % bis einschließlich 15 % | +15 |
| Momentum | Kursverlust über 10 % | −20 |
| Volatilität | Standardabweichung der Renditen pro Kursbalken über 2,5 % | +20 |
| Volatilität | Standardabweichung der Renditen pro Kursbalken unter 1 % | −10 |
| 52-Wochen-Hoch | Weniger als 3 % unter dem Hoch, auf dem Hoch oder darüber | +15 |
| 52-Wochen-Hoch | Mehr als 30 % unter dem Hoch | −10 |

Alle übrigen Werte bringen für das jeweilige Kriterium 0 Zusatzpunkte. Bei weniger als sechs gültigen Schlusskursen gibt die Funktion 50 Punkte zurück. Hohe Volatilität bringt auch dann Pluspunkte, wenn die Schwankungen überwiegend durch fallende Kurse entstanden sind.
