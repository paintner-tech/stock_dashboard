
# Mathematische Grundlagen

Diese Dokumentation beschreibt die mathematischen Grundlagen und Berechnungsverfahren, die im Aktien-Dashboard verwendet werden.

Ziel ist es, die Berechnungen nachvollziehbar zu machen und die verwendeten Kennzahlen verständlich zu erklären.

---

## 1. Gleitender Durchschnitt (Moving Average)

Ein gleitender Durchschnitt glättet Kursschwankungen und hilft dabei, Trends zu erkennen.

### 1.1 Simple Moving Average (SMA)

Der SMA berechnet den arithmetischen Mittelwert der Schlusskurse über einen definierten Zeitraum.

**Formel:**

$$
SMA_n = \frac{1}{n}\sum_{i=1}^{n}P_i
$$

Dabei gilt:

- $n$: Anzahl der betrachteten Handelstage
- $P_i$: Schlusskurs des jeweiligen Handelstages

**Verwendung im Dashboard:**

- SMA 20: kurzfristiger Trend
- SMA 50: mittelfristiger Trend
- SMA 200: langfristiger Trend

Ein Kurs oberhalb des SMA deutet auf eine positive Kursentwicklung gegenüber dem Durchschnitt hin. Ein Kurs unterhalb des SMA kann auf eine schwächere Entwicklung hindeuten.

---

## 2. Relative Strength Index (RSI)

Der RSI ist ein Momentum-Indikator, der die Stärke von Kursbewegungen bewertet.

### 2.1 Berechnung

Der RSI basiert auf dem Verhältnis durchschnittlicher Kursgewinne zu durchschnittlichen Kursverlusten.

$$
RS = \frac{\text{Durchschnittlicher Gewinn}}{\text{Durchschnittlicher Verlust}}
$$

$$
RSI = 100-\frac{100}{1+RS}
$$

Der Wertebereich liegt zwischen 0 und 100.

**Interpretation:**

- RSI über 70: häufig als überkauft interpretiert
- RSI unter 30: häufig als überverkauft interpretiert
- RSI um 50: ausgeglichenes Momentum

Ein überkaufter oder überverkaufter Zustand ist kein automatisches Kauf- oder Verkaufssignal.

---

## 3. Bollinger Bänder

Bollinger Bänder zeigen die relative Position des Aktienkurses zum gleitenden Durchschnitt sowie die aktuelle Kursschwankungsbreite.

### 3.1 Berechnung

Das mittlere Band entspricht einem SMA über 20 Handelstage.

$$
BB_{Middle}=SMA_{20}
$$

Die oberen und unteren Bänder werden anhand der Standardabweichung berechnet.

$$
BB_{Upper}=SMA_{20}+2\sigma
$$

$$
BB_{Lower}=SMA_{20}-2\sigma
$$

Dabei ist:

- $\sigma$: Standardabweichung der letzten 20 Schlusskurse
- Faktor 2: Abstand von zwei Standardabweichungen zum Mittelwert

### 3.2 Interpretation

- Kurs nahe dem unteren Band: relative Schwäche innerhalb der aktuellen Schwankungsbreite
- Kurs nahe dem oberen Band: relative Stärke innerhalb der aktuellen Schwankungsbreite
- Enge Bänder: geringe Volatilität
- Breite Bänder: hohe Volatilität

Das Berühren eines Bollinger Bandes ist kein automatisches Kauf- oder Verkaufssignal.

---

## 4. Standardabweichung

Die Standardabweichung beschreibt, wie stark einzelne Werte um ihren Mittelwert streuen.

Eine hohe Standardabweichung bedeutet größere Schwankungen, eine niedrige Standardabweichung bedeutet geringere Schwankungen.

Die Standardabweichung wird im Dashboard insbesondere für die Berechnung der Bollinger Bänder verwendet.

---

## 5. Prozentuale Kursveränderung

Die prozentuale Kursveränderung beschreibt die relative Veränderung eines Aktienkurses zwischen zwei Zeitpunkten.

$$
\text{Kursveränderung}=\frac{P_{neu}-P_{alt}}{P_{alt}}\times100
$$

Dabei gilt:

- $P_{neu}$: aktueller Kurs
- $P_{alt}$: Kurs zum Vergleichszeitpunkt

Positive Werte zeigen einen Kursanstieg, negative Werte einen Kursrückgang.

---

## 6. Verhältniskennzahlen

Verhältniskennzahlen setzen unterschiedliche Unternehmens- oder Kursgrößen ins Verhältnis.

Beispiele:

- KGV: Kurs-Gewinn-Verhältnis
- KBV: Kurs-Buchwert-Verhältnis
- KUV: Kurs-Umsatz-Verhältnis
- Dividendenrendite: Verhältnis der Dividende zum Aktienkurs

Diese Kennzahlen werden im Dashboard zur Bewertung von Aktien verwendet.

---

## 7. Scores und Bewertungsmodelle

Die verschiedenen Bewertungsmodelle des Dashboards kombinieren einzelne Kennzahlen zu einem Gesamtwert.

Die Berechnung der einzelnen Scores wird separat dokumentiert:

- Buy & Hold Score
- Buffett Score
- Trading Score
- Fundamentaldatenanalyse

Die Scores dienen der strukturierten Bewertung und stellen keine garantierte Prognose zukünftiger Kursentwicklungen dar.

