import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK & SETUP ---
DB_NAME = "watchlist_final_v200.db"
# Die kräftigen Farben für das äußere Modul (Blau, Grün, Lila, Petrol, Anthrazit)
OUTER_COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#0f766e", "#334155"]

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
    except: pass
    conn.close()

def remove_from_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()

def calc_rsi(series, period=14):
    if len(series) < period: return pd.Series([50]*len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Pro Tracker", layout="wide")
init_db()

# --- CSS: DAS IST DER ULTIMATIVE VARIABLEN-FIX ---
st.markdown("""
    <style>
    /* Basis App */
    .stApp { background-color: #0e1117 !important; }
    
    @media (min-width: 768px) {
        .main .block-container { max-width: 950px; margin: auto; }
    }

    /* 1. ÄUSSERES MODUL */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.outer-marker) {
        border-radius: 40px !important;
        border: none !important;
        padding: 30px !important;
        margin-bottom: 40px !important;
        /* Wir überschreiben die Streamlit-Variablen direkt im Element */
        --st-border-color: transparent;
    }

    /* HEADER LAYOUT */
    .custom-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 25px;
        width: 100%;
    }
    .box-info-left {
        background-color: #d1e8ff !important; 
        padding: 12px 20px;
        border-radius: 10px;
        color: #ff0000 !important;
        font-weight: bold;
        font-size: 1.2em;
        box-shadow: 3px 3px 10px rgba(0,0,0,0.2);
    }
    .box-rsi-right {
        background-color: #ffb400 !important; 
        padding: 12px 20px;
        border-radius: 10px;
        color: black !important;
        font-weight: bold;
        font-size: 1.4em;
        border: 2px solid black;
        box-shadow: 3px 3px 10px rgba(0,0,0,0.2);
    }

    /* 2. CHART BOX (PFIRSICH) - Wir überschreiben die Hintergrund-Variable */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-marker) {
        background-color: #f7cbb4 !important;
        --background-color: #f7cbb4;
        --secondary-background-color: #f7cbb4;
        border-radius: 20px !important;
        padding: 15px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        margin-bottom: 20px !important;
    }

    /* 3. BUTTON BOX (HELLGRÜN) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.button-marker) {
        background-color: #c4f3ce !important;
        --background-color: #c4f3ce;
        --secondary-background-color: #c4f3ce;
        border-radius: 15px !important;
        padding: 0px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
    }

    /* BUTTON TEXT & STYLE */
    div.stButton > button {
        background-color: transparent !important;
        color: #1a3d34 !important;
        border: none !important;
        height: 65px !important;
        font-size: 1.6em !important;
        font-weight: bold !important;
        width: 100% !important;
    }

    /* MOBILE OPTIMIERUNG */
    @media (max-width: 600px) {
        .custom-header { flex-direction: column; gap: 10px; }
        .box-info-left, .box-rsi-right { width: 100%; text-align: center; }
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
            opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Wähle:", opts.keys())
            if st.button("➕ Hinzufügen"):
                s = opts[sel]
                if s not in st.session_state.watchlist:
                    st.session_state.watchlist.append(s)
                    add_to_db(s)
                    st.rerun()
    except: pass

st.divider()

# --- ANZEIGE DER MODULE ---
if st.session_state.watchlist:
    # Daten laden
    all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)

    for i, ticker in enumerate(st.session_state.watchlist):
        color = OUTER_COLORS[i % len(OUTER_COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")
        
        # LEVEL 1: ÄUSSERER CONTAINER (FORCED COLOR)
        with st.container(border=True):
            st.markdown(f'<div class="outer-marker" id="out-{safe_id}"></div>', unsafe_allow_html=True)
            st.markdown(f"""
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#out-{safe_id}) {{
                    background-color: {color} !important;
                    --background-color: {color};
                    --secondary-background-color: {color};
                }}
                </style>
                """, unsafe_allow_html=True)
            
            try:
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    
                    # ISIN versuchen zu laden
                    try: isin = yf.Ticker(ticker).info.get('isin', '-')
                    except: isin = "-"

                    # HEADER BEREICH
                    st.markdown(f"""
                        <div class="custom-header">
                            <div class="box-info-left">{ticker} : {isin} &nbsp; {price:.2f}</div>
                            <div class="box-rsi-right">RSI (14): {rsi_v:.2f} - Neutral</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # LEVEL 2: CHART CONTAINER (FORCED PEACH)
                    with st.container(border=True):
                        st.markdown(f'<div class="chart-marker"></div>', unsafe_allow_html=True)
                        fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                        fig.add_hline(y=70, line_dash="dash", line_color="red")
                        fig.add_hline(y=30, line_dash="dash", line_color="green")
                        fig.update_layout(
                            height=220, margin=dict(l=10,r=10,t=10,b=10),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#1a3d5e", size=11),
                            xaxis=dict(showgrid=False), yaxis=dict(range=[0,100], showgrid=False)
                        )
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # LEVEL 3: BUTTON CONTAINER (FORCED GREEN)
                    with st.container(border=True):
                        st.markdown(f'<div class="button-marker"></div>', unsafe_allow_html=True)
                        if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker, use_container_width=True):
                            st.session_state.watchlist.remove(ticker)
                            remove_from_db(ticker)
                            st.rerun()

            except: continue
