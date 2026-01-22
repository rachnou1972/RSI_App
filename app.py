import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK & SETUP ---
DB_NAME = "watchlist_final_v25.db"
# Hintergrundfarben für die Aktien-Module (Blau, Dunkelgrün, Weinrot, Violett, Petrol)
MODULE_COLORS = ["#1e537d", "#145c48", "#7d1e3d", "#4b1e7d", "#1e727d"]


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
    if not data:
        return ["AAPL", "TSLA"]
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

# --- CSS FÜR DAS DESIGN (ERZWINGT FARBEN) ---
st.markdown("""
    <style>
    /* Hintergrund der App */
    .stApp { background-color: #0e1117; color: white; }

    /* Laptop-Zentrierung */
    @media (min-width: 768px) {
        .main .block-container { max-width: 950px; margin: auto; }
    }

    /* WICHTIG: Erzwingt die Farbe des Aktien-Moduls */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 30px !important;
        border: none !important;
        padding: 25px !important;
        margin-bottom: 20px !important;
    }

    /* HEADER BEREICH */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }

    /* Box Oben Links (Symbol & Preis) */
    .info-box {
        background-color: #d1e8ff; 
        padding: 8px 15px;
        border-radius: 5px;
        color: #ff0000 !important; /* Roter Text für Ticker */
        font-weight: bold;
        font-size: 1.1em;
    }

    /* Box Oben Rechts (RSI Bewertung) */
    .rsi-box-eval {
        background-color: #ffb400; 
        padding: 8px 15px;
        border-radius: 5px;
        color: black !important;
        font-weight: bold;
        font-size: 1.2em;
    }

    /* CHART BOX (Pfirsich) */
    /* Wir stylen den inneren Container des Charts */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f7cbb4 !important;
        border-radius: 15px !important;
        padding: 10px !important;
        margin-bottom: 15px !important;
    }

    /* BUTTON (Hellgrün) */
    div.stButton > button {
        background-color: #c4f3ce !important; 
        color: #1a3d34 !important;
        border-radius: 12px !important;
        height: 55px !important;
        font-size: 1.4em !important;
        font-weight: bold !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
        width: 100% !important;
    }

    /* Smartphone Optimierung */
    @media (max-width: 600px) {
        .header-container { flex-direction: column; gap: 8px; align-items: flex-start; }
        .rsi-box-eval, .info-box { width: 100%; font-size: 1em; text-align: center; }
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Aktie suchen (Name/ISIN/WKN):", placeholder="Tippen zum Suchen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Wähle:", options.keys())
            if st.button("➕ Hinzufügen", use_container_width=True):
                sym = options[sel]
                if sym not in st.session_state.watchlist:
                    st.session_state.watchlist.append(sym)
                    add_to_db(sym)
                    st.rerun()
    except:
        pass

st.divider()

# --- ANZEIGE DER MODULE ---
if st.session_state.watchlist:
    # Daten laden
    try:
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        bg_modul = MODULE_COLORS[i % len(MODULE_COLORS)]

        # INJEKTION DER MODUL-FARBE BASIEREND AUF DER POSITION (unfehlbar)
        # Wir zielen auf das (i+4). Element im Haupt-Layout ab (Title, Search, Divider sind davor)
        child_index = i + 5
        st.markdown(f"""
            <style>
            div[data-testid="stMain"] div[data-testid="stVerticalBlock"] > div:nth-child({child_index}) > div[data-testid="stVerticalBlockBorderWrapper"] {{
                background-color: {bg_modul} !important;
            }}
            </style>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            try:
                if len(st.session_state.watchlist) > 1:
                    df = all_data.xs(ticker, axis=1, level=1)
                else:
                    df = all_data

                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    eval_text = "Überkauft" if rsi_v > 70 else ("Überverkauft" if rsi_v < 30 else "Neutral")

                    # STUFE 1: HEADER
                    st.markdown(f"""
                        <div class="header-container">
                            <div class="info-box">{ticker} : {price:.2f}</div>
                            <div class="rsi-box-eval">RSI (14): {rsi_v:.2f} - {eval_text}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART IN PFIRSICH BOX
                    with st.container(border=True):
                        fig = go.Figure(
                            go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                        fig.add_hline(y=70, line_dash="dash", line_color="red")
                        fig.add_hline(y=30, line_dash="dash", line_color="green")
                        fig.update_layout(
                            height=220, margin=dict(l=10, r=10, t=10, b=10),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#1a3d5e", size=11),
                            xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                        )
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # STUFE 3: BUTTON
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
            except:
                st.error(f"Fehler bei {ticker}")