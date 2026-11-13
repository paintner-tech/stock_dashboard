
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ============================================================
# RSI – Berechnung nach Wilder
# ============================================================

def calculate_rsi(data, window=14):
    """
    Berechnet den klassischen Relative Strength Index
    nach der Methode von J. Welles Wilder.
    """

    delta = data.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / window,
        min_periods=window,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / window,
        min_periods=window,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    # Sonderfälle berücksichtigen
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50)

    return rsi


# ============================================================
# Währungsumrechnung
# ============================================================

def convert_history_to_eur(hist, currency):
    """
    Rechnet historische Kursdaten anhand des aktuellen
    EUR-Wechselkurses in Euro um.

    Hinweis:
    Die historischen Kurse werden mit dem aktuellen
    Wechselkurs umgerechnet, nicht mit historischen FX-Kursen.
    """

    currency = str(currency or "EUR").upper()

    if currency == "EUR" or hist.empty:
        return hist, currency, None

    try:
        fx_ticker = f"EUR{currency}=X"

        fx_data = yf.Ticker(fx_ticker).history(
            period="5d",
            interval="1d"
        )

        if fx_data.empty:
            raise ValueError("Keine Wechselkursdaten verfügbar.")

        rate = fx_data["Close"].dropna().iloc[-1]

        if pd.isna(rate) or rate <= 0:
            raise ValueError("Ungültiger Wechselkurs.")

        hist = hist.copy()

        for col in ["Open", "High", "Low", "Close"]:
            if col in hist.columns:
                hist[col] = hist[col] / rate

        return hist, "EUR", (
            f"Umrechnung von {currency} in EUR mit aktuellem "
            f"Wechselkurs ({rate:.4f} {currency}/EUR)."
        )

    except Exception as e:
        return hist, currency, (
            f"Keine EUR-Umrechnung möglich: {e}"
        )


# ============================================================
# CHART-ANALYSE DIALOG
# ============================================================

@st.dialog("🔍 Technische Chartanalyse & Crashkurs", width="large")
def show_chart_analysis_dialog(ticker, initial_hist, info):
    """
    Interaktive technische Chartanalyse.

    Funktionen:
    - Zeitraum-Auswahl
    - SMA 50 und SMA 200
    - RSI nach Wilder
    - Bollinger Bänder
    - Support und Resistance
    - Automatische und manuelle Y-Achsen-Skalierung
    - Interaktives Zoomen und Verschieben
    - Automatische technische Zusammenfassung
    """

    currency = info.get("currency", "EUR")
    company_name = info.get("shortName", ticker)

    st.markdown(
        f"### Chart-Analyse für: **{company_name} ({ticker})**"
    )

    # --------------------------------------------------------
    # ZEITRAUM-AUSWAHL
    # --------------------------------------------------------

    tf_options = {
        "1 Tag (1d)": ("1d", "5m", "5-Minuten-Kerzen"),
        "1 Woche (7d)": ("5d", "1h", "Stunden"),
        "1 Monat (1mo)": ("1mo", "1d", "Tage"),
        "3 Monate (3mo)": ("3mo", "1d", "Tage"),
        "6 Monate (6mo)": ("6mo", "1d", "Tage"),
        "1 Jahr (1y)": ("1y", "1d", "Tage"),
        "5 Jahre (5y)": ("5y", "1d", "Tage")
    }

    selected_tf_label = st.selectbox(
        "📅 Zeitraum für Detail-Chart wählen:",
        list(tf_options.keys()),
        index=2,
        key=f"dialog_tf_{ticker}"
    )

    period_val, interval_val, period_unit = tf_options[
        selected_tf_label
    ]

    # --------------------------------------------------------
    # HISTORISCHE DATEN LADEN
    # --------------------------------------------------------

    with st.spinner(f"Lade Historie für {selected_tf_label} ..."):

        try:
            stock = yf.Ticker(ticker)

            hist = stock.history(
                period=period_val,
                interval=interval_val
            )

        except Exception as e:
            st.error(f"Fehler beim Laden der Kursdaten: {e}")
            return

        if hist.empty or len(hist) < 2:
            st.warning(
                "Nicht genügend historische Daten für "
                "den gewählten Zeitraum vorhanden."
            )
            return

        # Währungsumrechnung
        hist, currency, fx_note = convert_history_to_eur(
            hist,
            info.get("currency", "USD")
        )

    if fx_note:
        st.caption(fx_note)

    # --------------------------------------------------------
    # DATEN AUFBEREITEN
    # --------------------------------------------------------

    df = hist.copy()

    required_columns = ["Close", "High", "Low"]

    if not all(col in df.columns for col in required_columns):
        st.error("Die geladenen Kursdaten sind unvollständig.")
        return

    df = df.dropna(subset=["Close", "High", "Low"])

    if len(df) < 2:
        st.warning("Nicht genügend verwertbare Kursdaten.")
        return

    # --------------------------------------------------------
    # TECHNISCHE INDIKATOREN
    # --------------------------------------------------------

    # Gleitende Durchschnitte
    df["SMA_50"] = df["Close"].rolling(
        window=50,
        min_periods=50
    ).mean()

    df["SMA_200"] = df["Close"].rolling(
        window=200,
        min_periods=200
    ).mean()

    # RSI
    df["RSI"] = calculate_rsi(
        df["Close"],
        window=14
    )

    # Bollinger Bänder
    df["BB_Middle"] = df["Close"].rolling(
        window=20
    ).mean()

    std = df["Close"].rolling(
        window=20
    ).std()

    df["BB_Upper"] = df["BB_Middle"] + (std * 2)
    df["BB_Lower"] = df["BB_Middle"] - (std * 2)

    # --------------------------------------------------------
    # SUPPORT UND RESISTANCE
    # --------------------------------------------------------

    # Die letzten 90 Kerzen werden ausgewertet.
    recent_df = df.tail(90)

    #support_level = recent_df["Low"].min()
    support_level = recent_df["Low"].quantile(0.05)
    resistance_level = recent_df["High"].quantile(0.95)

    # --------------------------------------------------------
    # CHART ERSTELLEN
    # --------------------------------------------------------

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.75, 0.25]
    )

    # --------------------------------------------------------
    # 1. KURSKURVE
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="Schlusskurs",
            line=dict(
                color="#1f77b4",
                width=2
            )
        ),
        row=1,
        col=1
    )

    # SMA 50
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA_50"],
            mode="lines",
            name=f"SMA 50 ({period_unit})",
            line=dict(
                color="orange",
                width=1.5,
                dash="dash"
            )
        ),
        row=1,
        col=1
    )

    # SMA 200
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA_200"],
            mode="lines",
            name=f"SMA 200 ({period_unit})",
            line=dict(
                color="red",
                width=1.5
            )
        ),
        row=1,
        col=1
    )

    # --------------------------------------------------------
    # BOLLINGER BÄNDER
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["BB_Lower"],
            mode="lines",
            name="Bollinger Unterseite",
            line=dict(
                color="rgba(150,150,150,0.5)",
                width=1
            )
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["BB_Upper"],
            mode="lines",
            name="Bollinger Oberseite",
            line=dict(
                color="rgba(150,150,150,0.5)",
                width=1
            ),
            fill="tonexty",
            fillcolor="rgba(150,150,150,0.08)"
        ),
        row=1,
        col=1
    )

    # --------------------------------------------------------
    # SUPPORT UND RESISTANCE
    # --------------------------------------------------------

    fig.add_hline(
        y=support_level,
        line_dash="dash",
        line_color="green",
        row=1,
        col=1,
        annotation_text=(
            f"Support: {support_level:.2f} {currency}"
        ),
        annotation_position="top left"
    )

    fig.add_hline(
        y=resistance_level,
        line_dash="dash",
        line_color="red",
        row=1,
        col=1,
        annotation_text=(
            f"Widerstand: {resistance_level:.2f} {currency}"
        ),
        annotation_position="top left"
    )

    # --------------------------------------------------------
    # 2. RSI
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI"],
            mode="lines",
            name="RSI (14)",
            line=dict(
                color="#9467bd",
                width=1.5
            )
        ),
        row=2,
        col=1
    )

    fig.add_hline(
        y=70,
        line_dash="dot",
        line_color="red",
        row=2,
        col=1,
        annotation_text="Überkauft (70)",
        annotation_position="top left"
    )

    fig.add_hline(
        y=30,
        line_dash="dot",
        line_color="green",
        row=2,
        col=1,
        annotation_text="Überverkauft (30)",
        annotation_position="bottom left"
    )

    # --------------------------------------------------------
    # CHART LAYOUT
    # --------------------------------------------------------

    fig.update_layout(
        height=600,

        margin=dict(
            l=20,
            r=20,
            t=40,
            b=20
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),

        dragmode="zoom",

        hovermode="x unified",

        xaxis_rangeslider_visible=False,

        yaxis=dict(
            side="left",
            title=f"Kurs ({currency})",
            autorange=True
        ),

        yaxis2=dict(
            side="left",
            title="RSI",
            range=[0, 100]
        ),

        # Zoom bei Streamlit-Neuberechnungen möglichst erhalten
        uirevision=f"{ticker}_{selected_tf_label}"
    )

    # --------------------------------------------------------
    # INTERAKTIVE SKALIERUNG
    # --------------------------------------------------------

    st.markdown("### 📐 Chart-Skalierung")

    scale_mode = st.radio(
        "Vertikale Kursskalierung:",
        [
            "Automatisch",
            "Manuell"
        ],
        horizontal=True,
        key=f"scale_mode_{ticker}"
    )

    if scale_mode == "Manuell":

        default_min = float(df["Low"].min() * 0.95)
        default_max = float(df["High"].max() * 1.05)

        col_min, col_max = st.columns(2)

        with col_min:
            y_min = st.number_input(
                "Kursachse von",
                value=default_min,
                format="%.2f",
                key=f"y_min_{ticker}_{selected_tf_label}"
            )

        with col_max:
            y_max = st.number_input(
                "Kursachse bis",
                value=default_max,
                format="%.2f",
                key=f"y_max_{ticker}_{selected_tf_label}"
            )

        if y_min < y_max:

            fig.update_yaxes(
                range=[y_min, y_max],
                autorange=False,
                row=1,
                col=1
            )

        else:
            st.warning(
                "Der Maximalwert muss größer als "
                "der Minimalwert sein."
            )

    else:

        fig.update_yaxes(
            autorange=True,
            row=1,
            col=1
        )

    st.caption(
        "Tipp: Du kannst auch direkt im Chart mit der Maus "
        "einen Bereich markieren, hineinzoomen und den "
        "sichtbaren Kursbereich verschieben. Ein Doppelklick "
        "setzt den Zoom zurück. Die manuelle Skalierung "
        "verändert nur die Darstellung, nicht die Kursdaten."
    )

    # --------------------------------------------------------
    # CHART ANZEIGEN
    # --------------------------------------------------------

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToAdd": [
                "drawline",
                "drawrect",
                "eraseshape"
            ]
        }
    )

    # --------------------------------------------------------
    # AUTOMATISCHE AUSWERTUNG
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "🤖 Automatische Auswertung dieser Aktie"
    )

    last_price = df["Close"].iloc[-1]

    sma_50 = df["SMA_50"].iloc[-1]
    sma_200 = df["SMA_200"].iloc[-1]
    rsi_val = df["RSI"].iloc[-1]

    sma_50 = None if pd.isna(sma_50) else sma_50
    sma_200 = None if pd.isna(sma_200) else sma_200
    rsi_val = None if pd.isna(rsi_val) else rsi_val

    col_i1, col_i2, col_i3 = st.columns(3)

    # --------------------------------------------------------
    # TREND-CHECK
    # --------------------------------------------------------

    with col_i1:

        st.markdown("**1. Trend-Check**")

        if sma_200 is not None:

            if last_price > sma_200:

                st.success(
                    f"Kurs über SMA 200 "
                    f"({sma_200:.2f} {currency})."
                )

            else:

                st.error(
                    f"Kurs unter SMA 200 "
                    f"({sma_200:.2f} {currency})."
                )

        else:

            st.info(
                "Zu wenig Historie für SMA 200."
            )

        if sma_50 is not None:

            if last_price > sma_50:

                st.write(
                    f"Kurs über SMA 50 ({sma_50:.2f})."
                )

            else:

                st.write(
                    f"Kurs unter SMA 50 ({sma_50:.2f})."
                )

    # --------------------------------------------------------
    # RSI-CHECK
    # --------------------------------------------------------

    with col_i2:

        st.markdown("**2. RSI-Check**")

        if rsi_val is not None:

            if rsi_val > 70:

                st.warning(
                    f"RSI bei **{rsi_val:.1f}** "
                    "(Überkauft)."
                )

            elif rsi_val < 30:

                st.success(
                    f"RSI bei **{rsi_val:.1f}** "
                    "(Überverkauft)."
                )

            else:

                st.info(
                    f"RSI bei **{rsi_val:.1f}** "
                    "(Neutral)."
                )

        else:

            st.info("Noch nicht genügend Daten für RSI.")

    # --------------------------------------------------------
    # SUPPORT / RESISTANCE
    # --------------------------------------------------------

    with col_i3:

        st.markdown("**3. Support & Resistance**")

        st.info(
            f"S: {support_level:.2f}\n\n"
            f"R: {resistance_level:.2f} {currency}"
        )

        support_distance = (
            (last_price - support_level) / last_price
        ) * 100

        resistance_distance = (
            (resistance_level - last_price) / last_price
        ) * 100

        st.caption(
            f"Abstand Support: {support_distance:.1f}%"
        )

        st.caption(
            f"Abstand Widerstand: "
            f"{resistance_distance:.1f}%"
        )

    # --------------------------------------------------------
    # AUTOMATISCHE ZUSAMMENFASSUNG
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "💡 Technische Zusammenfassung"
    )

    summary_points = []

    # Langfristiger Trend
    if sma_200 is not None:

        if last_price > sma_200:

            summary_points.append(
                "Der Kurs liegt über dem **SMA 200**. "
                "Der langfristige Trend ist damit positiv."
            )

        else:

            summary_points.append(
                "Der Kurs liegt unter dem **SMA 200**. "
                "Der langfristige Trend ist aktuell negativ."
            )

    else:

        summary_points.append(
            "Der langfristige Trend kann mangels "
            "historischer Daten nicht beurteilt werden."
        )

    # Mittelfristiger Trend
    if sma_50 is not None:

        if last_price > sma_50:

            summary_points.append(
                "Der Kurs liegt über dem **SMA 50**. "
                "Der mittelfristige Trend ist positiv."
            )

        else:

            summary_points.append(
                "Der Kurs liegt unter dem **SMA 50**. "
                "Der mittelfristige Trend ist aktuell negativ."
            )

    # RSI
    if rsi_val is not None:

        if rsi_val > 70:

            summary_points.append(
                f"Der RSI liegt bei **{rsi_val:.1f}**. "
                "Die Aktie ist kurzfristig überkauft. "
                "Rücksetzer sind möglich."
            )

        elif rsi_val < 30:

            summary_points.append(
                f"Der RSI liegt bei **{rsi_val:.1f}**. "
                "Die Aktie ist kurzfristig überverkauft. "
                "Eine technische Gegenbewegung ist möglich, "
                "aber nicht garantiert."
            )

        else:

            summary_points.append(
                f"Der RSI liegt bei **{rsi_val:.1f}** "
                "im neutralen Bereich."
            )

    # Abstand zu Support und Resistance
    if support_distance < resistance_distance:

        summary_points.append(
            f"Der Kurs liegt näher an der bisherigen "
            f"**Unterstützung ({support_level:.2f} {currency})**. "
            "Die Zone sollte auf eine mögliche Stabilisierung "
            "beobachtet werden."
        )

    else:

        summary_points.append(
            f"Der Kurs liegt näher am bisherigen "
            f"**Widerstand ({resistance_level:.2f} {currency})**. "
            "Ein Ausbruch oder eine erneute Abweisung "
            "sind möglich."
        )

    for point in summary_points:
        st.markdown(f"- {point}")

    st.caption(
        "Die technische Auswertung basiert ausschließlich "
        "auf historischen Kursdaten und ist keine "
        "eigenständige Kauf- oder Verkaufsempfehlung."
    )

    # --------------------------------------------------------
    # CRASHKURS
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "📚 Crashkurs: Die Indikatoren verstehen"
    )

    with st.expander(
        "📌 Was sind Unterstützungen (Support) & Widerstände?"
    ):

        st.markdown("""
        * **Unterstützung:** Eine Preisregion, in der die Aktie
          in der Vergangenheit häufiger Käufer gefunden hat.
        * **Widerstand:** Eine Preisregion, an der die Aktie
          in der Vergangenheit häufiger auf Verkaufsdruck
          gestoßen ist.

        Die hier eingezeichneten Linien zeigen lediglich das
        niedrigste Tief und das höchste Hoch der letzten
        90 Kerzen. Sie sind keine automatisch ermittelten
        technischen Zonen.
        """)

    with st.expander(
        "📌 Was ist die SMA 50 & SMA 200?"
    ):

        st.markdown("""
        * **SMA 50:** Durchschnittskurs der letzten 50 Kerzen.
          Bei Tagescharts entspricht das ungefähr 2,5 Monaten.
        * **SMA 200:** Durchschnittskurs der letzten 200 Kerzen.
          Bei Tagescharts entspricht das ungefähr 200 Handelstagen.

        Liegt der Kurs über dem jeweiligen Durchschnitt,
        spricht das für einen positiven Trend.

        Liegt er darunter, spricht das für einen schwächeren Trend.

        Wichtig: Bei Stunden- oder Minutencharts beziehen sich
        die Durchschnitte auf die jeweilige Kerzeneinheit.
        """)

    with st.expander(
        "📌 Was ist der RSI (Relative Strength Index)?"
    ):

        st.markdown("""
        Der RSI vergleicht die durchschnittlichen Kursgewinne
        mit den durchschnittlichen Kursverlusten der letzten
        14 Perioden.

        * **Über 70:** Überkauft – kurzfristig erhöhte
          Rücksetzergefahr.
        * **Unter 30:** Überverkauft – eine Gegenbewegung
          könnte bevorstehen.
        * **Zwischen 30 und 70:** Neutraler Bereich.

        Ein überverkaufter RSI bedeutet nicht automatisch,
        dass eine Aktie ihren Boden erreicht hat.
        In starken Abwärtstrends kann der RSI lange niedrig bleiben.
        """)

    with st.expander(
        "📌 Was sind die Bollinger Bänder?"
    ):

        st.markdown("""
        Die Bollinger Bänder bestehen aus einem gleitenden
        Durchschnitt über 20 Perioden und zwei äußeren Bändern,
        die jeweils zwei Standardabweichungen entfernt liegen.

        * **Oberes Band:** Der Kurs befindet sich relativ weit
          oberhalb seines Durchschnitts.
        * **Unteres Band:** Der Kurs befindet sich relativ weit
          unterhalb seines Durchschnitts.
        * **Enge Bänder:** Die Schwankungsbreite ist gering.
        * **Weite Bänder:** Die Schwankungsbreite ist hoch.

        Ein Berühren des oberen oder unteren Bandes ist
        allein kein Kauf- oder Verkaufssignal.
        """)

    # --------------------------------------------------------
    # SCHLIESSEN
    # --------------------------------------------------------

    st.write("")

    if st.button(
        "Schließen",
        use_container_width=True
    ):
        st.rerun()

