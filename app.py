import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK ---
DB_NAME = "watchlist_final_master.db"
# Kräftige Farben für das umschließende Modul
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#0f766e", "#334155"]

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
st.set_page_config(page_title="RSI Tracker", layout="wide")
init_db()

# --- CSS: DAS ERZWINGT DIE FARBEN AUCH IN DER CLOUD ---
st.markdown("""
    <style>
    /* Hintergrund der Seite */
    .stApp { background-color: #0e1117 !important; }
    
    /* Laptop-Zentrierung (850px breit und mittig) */
    @media (min-width: 768px) {
        .main .block-container { 
            max-width: 850px !important; 
            margin: auto !important; 
            padding-top: 2rem !important;
        }
    }

    /* 1. DAS GESAMTE MODUL (UMSCHLIESSENDER RAHMEN) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.outer-marker) {
        border-radius: 40px !important;
        border: none !important;
        padding: 0px !important;
        margin-bottom: 50px !important;
        overflow: hidden !important;
    }
    
    /* Entfernt Abstände zwischen den Elementen im Modul */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.outer-marker) > div[data-testid="stVerticalBlock"] {
        gap: 0px !important;
    }

    /* 2. STUFE: HEADER BEREICH */
    .header-box {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 25px 25px 15px 25px;
        width: 100%;
    }
    .tag-info {
        background-color: #d1e8ff; padding: 10px 20px; border-radius: 8px;
        color: #ff0000 !important; font-weight: bold; font-size: 1.1em;
    }
    .tag-rsi {
        background-color: #ffb400; padding: 10px 20px; border-radius: 8px;
        color: black !important; font-weight: bold; font-size: 1.3em; border: 2px solid black;
    }

    /* 3. STUFE: CHART CONTAINER (PFIRSICH) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-marker) {
        background-color: #f7cbb4 !important;
        margin: 0 25px 20px 25px !important;
        border-radius: 20px !important;
        padding: 15px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
    }

    /* 4. STUFE: BUTTON CONTAINER (GRÜN) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.button-marker) {
        background-color: #c4f3ce !important;
        margin: 0 25px 30px 25px !important;
        border-radius: 15px !important;
        padding: 0px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
    }

    /* Button Styling */
    div.stButton > button {
        background-color: transparent !important;
        color: #1a3d34 !important;
        border: none !important;
        height: 60px !important;
        font-size: 1.5em !important;
        font-weight: bold !important;
        width: 100% !important;
    }

    /* Smartphone Optimierung */
    @media (max-width: 600px) {
        .header-box { flex-direction: column; gap: 10px; padding: 20px 15px; }
        .tag-info, .tag-rsi { width: 100%; text-align: center; }
    }
    
    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# SUCHE
search = st.text_input("Aktie suchen (Name/ISIN/WKN):", placeholder="Hier tippen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Ergebnis wählen:", opts.keys())
            if st.button("➕ Hinzufügen", key="add_btn"):
                s = opts[sel]
                if s not in st.session_state.watchlist:
                    st.session_state.watchlist.append(s)
                    add_to_db(s)
                    st.rerun()
    except: pass

st.divider()

# --- ANZEIGE DER MODULE NACH ZEICHNUNG ---
if st.session_state.watchlist:
    # Daten Batch-Download
    all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)

    for i, ticker in enumerate(st.session_state.watchlist):
        color = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")
        
        # --- LEVEL 1: ÄUSSERER CONTAINER ---
        # Wir erzeugen ein modulspezifisches CSS für JEDEN Ticker einzeln.
        st.markdown(f"""
            <style>
            div[data-testid="stVerticalBlockBorderWrapper"]:has(#outer-{safe_id}) {{
                background-color: {color} !important;
            }}
            </style>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            # Der Marker identifiziert diesen Block
            st.markdown(f'<div class="outer-marker" id="outer-{safe_id}"></div>', unsafe_allow_html=True)
            
            try:
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    eval_txt = "Überkauft" if rsi_v > 70 else ("Überverkauft" if rsi_v < 30 else "Neutral")

                    # HEADER BEREICH (INFO & RSI)
                    st.markdown(f"""
                        <div class="header-box">
                            <div class="tag-info">{ticker} : {price:.2f}</div>
                            <div class="tag-rsi">RSI (14): {rsi_v:.2f} - {eval_txt}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # --- LEVEL 2: CHART CONTAINER (PFIRSICH) ---
                    with st.container(border=True):
                        st.markdown('<div class="chart-marker"></div>', unsafe_allow_html=True)
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

                    # --- LEVEL 3: BUTTON CONTAINER (HELLGRÜN) ---
                    with st.container(border=True):
                        st.markdown('<div class="button-marker"></div>', unsafe_allow_html=True)
                        if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker, use_container_width=True):
                            st.session_state.watchlist.remove(ticker)
                            remove_from_db(ticker)
                            st.rerun()

            except: continue
