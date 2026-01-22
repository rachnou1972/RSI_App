import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION & DATENBANK ---
DB_NAME = "watchlist_final_fix.db"
# Kräftige Modul-Farben
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#312e81", "#134e4a"]


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
st.set_page_config(page_title="RSI Tracker Ultimate", layout="wide")
init_db()

# --- CSS: DAS ERZWINGT DIE FARBEN UND DAS LAYOUT ---
st.markdown("""
    <style>
    /* Hintergrund der App */
    .stApp { background-color: #0e1117 !important; }

    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* WICHTIG: Färbt den gesamten Block inkl. Abstände */
    div[data-testid="stVerticalBlock"]:has(> div > div > .color-wrapper) {
        gap: 0px !important;
    }

    /* Das umschließende farbige Modul */
    .full-module-box {
        border-radius: 35px;
        padding: 25px;
        margin-bottom: 35px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        border: none;
    }

    /* Header Zeile */
    .header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        width: 100%;
    }

    /* Box Links: Symbol, ISIN, Preis */
    .info-box-left {
        background-color: #d1e8ff; 
        padding: 10px 18px;
        border-radius: 8px;
        color: #ff0000; /* Ticker in Rot */
        font-weight: bold;
        font-size: 1.1em;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        display: flex;
        gap: 10px;
    }

    /* Box Rechts: RSI Bewertung */
    .rsi-box-right {
        background-color: #ffb400; 
        padding: 10px 18px;
        border-radius: 8px;
        color: black;
        font-weight: bold;
        font-size: 1.3em;
        border: 2px solid black;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    /* Chart Bereich (Pfirsich) */
    .chart-container-peach {
        background-color: #f7cbb4; 
        border-radius: 20px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid rgba(0,0,0,0.1);
    }

    /* Button Bereich (Hellgrün) */
    div.stButton > button {
        background-color: #c4f3ce !important; 
        color: #1a3d34 !important;
        border-radius: 15px !important;
        height: 60px !important;
        width: 100% !important;
        font-size: 1.5em !important;
        font-weight: bold !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }

    /* Mobile Anpassung */
    @media (max-width: 600px) {
        .header-row { flex-direction: column; gap: 10px; align-items: flex-start; }
        .info-box-left, .rsi-box-right { width: 100%; text-align: center; justify-content: center; }
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Aktie suchen (Name/ISIN/Ticker):", placeholder="Tippen zum Suchen...")
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

# --- ANZEIGE DER MODULE NACH ZEICHNUNG ---
if st.session_state.watchlist:
    try:
        # Batch Download für Speed
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.error("Datenfehler beim Abruf.")
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        color = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")

        try:
            # Daten Extraktion
            if len(st.session_state.watchlist) > 1:
                df = all_data.xs(ticker, axis=1, level=1)
            else:
                df = all_data

            if not df.empty:
                # ISIN laden (optional)
                isin = "-"
                rsi_v = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]
                eval_txt = "Überkauft" if rsi_v > 70 else ("Überverkauft" if rsi_v < 30 else "Neutral")

                # START DES FARBIGEN MODULS
                st.markdown(f"""
                <div class="color-wrapper" id="wrapper-{safe_id}"></div>
                <style>
                /* Dieser Trick färbt den Streamlit-Container von innen heraus */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#wrapper-{safe_id}) {{
                    background-color: {color} !important;
                    border: none !important;
                    border-radius: 35px !important;
                    padding: 25px !important;
                    margin-bottom: 35px !important;
                }}
                </style>
                <div class="header-row">
                    <div class="info-box-left">{ticker} : {isin} &nbsp; {price:.2f}</div>
                    <div class="rsi-box-right">RSI (14): {rsi_v:.2f} - {eval_txt}</div>
                </div>
                """, unsafe_allow_html=True)

                # STUFE 2: CHART IN PFIRSICH BOX
                st.markdown('<div class="chart-container-peach">', unsafe_allow_html=True)
                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                fig.add_hline(y=30, line_dash="dash", line_color="green")
                fig.update_layout(
                    height=220, margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor='#f7cbb4', plot_bgcolor='#f7cbb4',  # Pfirsich
                    font=dict(color="#1a3d5e", size=11),
                    xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)

                # STUFE 3: BUTTON IN HELLGRÜN
                if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                    st.session_state.watchlist.remove(ticker)
                    remove_from_db(ticker)
                    st.rerun()

            else:
                st.warning(f"Keine Daten für {ticker}")
        except:
            continue