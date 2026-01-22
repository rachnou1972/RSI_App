import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK ---
DB_NAME = "watchlist_final_v30.db"
# Kräftige Modul-Farben (Blau, Grün, Lila, Petrol, Anthrazit)
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#0f766e", "#1e40af"]


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()


def load_watchlist():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT symbol FROM watchlist')
    data = [row[0] for row in c.fetchall()]
    conn.close()
    if not data: return ["AAPL", "TSLA"]
    return data


def add_to_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('INSERT OR REPLACE INTO watchlist VALUES (?)', (symbol,))
        conn.commit()
    except:
        pass
    conn.close()


def remove_from_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()


def calc_rsi(series, period=14):
    if len(series) < period: return pd.Series([50] * len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Pro Tracker", layout="wide")
init_db()

# --- CSS: DAS IST DIE LÖSUNG FÜR DIE FARBEN ---
st.markdown("""
    <style>
    /* Basis App */
    .stApp { background-color: #0e1117 !important; }

    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* DAS MODUL (UMSCHLIESSENDES ELEMENT) */
    /* Wir nutzen eine spezielle Technik, um den schwarzen Hintergrund zu verdrängen */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.module-marker) {
        background-color: transparent !important;
        border: none !important;
        padding: 0px !important;
    }

    /* Das eigentliche farbige Rechteck */
    .full-module {
        border-radius: 30px;
        padding: 25px;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        display: block;
        width: 100%;
    }

    /* Header Zeile */
    .row-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 10px;
    }

    .info-tag {
        background: rgba(255,255,255,0.9);
        padding: 8px 15px;
        border-radius: 8px;
        color: #d32f2f;
        font-weight: bold;
        font-size: 1.1em;
    }

    .rsi-tag {
        background: #ffcc00;
        padding: 8px 15px;
        border-radius: 8px;
        color: black;
        font-weight: bold;
        font-size: 1.2em;
        border: 2px solid black;
    }

    /* Chart Bereich (Pfirsich) */
    .chart-area {
        background-color: #f7cbb4;
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 15px;
        border: 2px solid rgba(0,0,0,0.1);
    }

    /* Button Bereich (Grün) */
    div.stButton > button {
        background-color: #c4f3ce !important;
        color: #1a3d34 !important;
        border-radius: 15px !important;
        height: 55px !important;
        width: 100% !important;
        font-size: 1.3em !important;
        font-weight: bold !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
    }

    /* Mobile Fixes */
    @media (max-width: 600px) {
        .full-module { padding: 15px; }
        .info-tag, .rsi-tag { width: 100%; text-align: center; }
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Aktie / ISIN / WKN suchen:", placeholder="Tippen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Wähle:", opts.keys())
            if st.button("➕ Hinzufügen", use_container_width=True):
                s = opts[sel]
                if s not in st.session_state.watchlist:
                    st.session_state.watchlist.append(s)
                    add_to_db(s)
                    st.rerun()
    except:
        pass

st.divider()

# --- ANZEIGE ---
if st.session_state.watchlist:
    # Daten Batch-Download
    try:
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.error("Verbindung zu Yahoo fehlgeschlagen.")
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        color = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")

        # WIR BAUEN DAS MODUL MANUELL MIT HTML UM DIE FARBEN ZU ERZWINGEN
        try:
            if len(st.session_state.watchlist) > 1:
                df = all_data.xs(ticker, axis=1, level=1)
            else:
                df = all_data

            if not df.empty:
                rsi_v = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]
                eval_txt = "Überkauft" if rsi_v > 70 else ("Überverkauft" if rsi_v < 30 else "Neutral")

                # START MODUL (Umschließendes farbiges Element)
                st.markdown(f"""
                <div class="module-marker" id="m-{safe_id}"></div>
                <div class="full-module" style="background-color: {color};">
                    <div class="row-header">
                        <div class="info-tag">{ticker} : {price:.2f}</div>
                        <div class="rsi-tag">RSI (14): {rsi_v:.2f} - {eval_txt}</div>
                    </div>
                """, unsafe_allow_html=True)

                # MITTE: CHART (In Pfirsich Box)
                st.markdown('<div class="chart-area">', unsafe_allow_html=True)
                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                fig.add_hline(y=30, line_dash="dash", line_color="green")
                fig.update_layout(
                    height=200, margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',  # Nimmt Pfirsich-Farbe an
                    font=dict(color="#1a3d5e", size=11),
                    xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)

                # UNTEN: BUTTON (In Grün Box)
                if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                    st.session_state.watchlist.remove(ticker)
                    remove_from_db(ticker)
                    st.rerun()

                # ENDE MODUL
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning(f"Keine Daten für {ticker}")
        except:
            continue