import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION & DATENBANK ---
DB_NAME = "watchlist_ultimate_pro_v1.db"
# Kräftige Farben für die Modul-Hintergründe
OUTER_COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#312e81", "#134e4a"]

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

# --- CSS: DAS ERZWINGT DIE VERSCHACHTELTEN FARBEN ---
st.markdown("""
    <style>
    /* Basis Hintergrund */
    .stApp { background-color: #0e1117 !important; }
    
    @media (min-width: 768px) {
        .main .block-container { max-width: 950px; margin: auto; }
    }

    /* 1. ÄUSSERER RAHMEN (MODUL) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.outer-anchor) {
        border-radius: 40px !important;
        border: none !important;
        padding: 30px !important;
        margin-bottom: 40px !important;
        overflow: hidden !important;
    }

    /* HEADER LAYOUT */
    .header-flex {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        width: 100%;
    }
    .info-box-styled {
        background-color: #d1e8ff; 
        padding: 10px 20px;
        border-radius: 8px;
        color: #ff0000 !important;
        font-weight: bold;
        font-size: 1.2em;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .rsi-box-styled {
        background-color: #ffb400; 
        padding: 10px 20px;
        border-radius: 8px;
        color: black !important;
        font-weight: bold;
        font-size: 1.4em;
        border: 2px solid black;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    /* 2. CHART CONTAINER (PFIRSICH) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-anchor) {
        background-color: #f7cbb4 !important;
        border-radius: 20px !important;
        padding: 15px !important;
        border: none !important;
        margin-bottom: 20px !important;
    }

    /* 3. BUTTON CONTAINER (HELLGRÜN) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.button-anchor) {
        background-color: #c4f3ce !important;
        border-radius: 15px !important;
        padding: 0px !important;
        border: none !important;
    }

    /* BUTTON TEXT */
    div.stButton > button {
        background-color: transparent !important;
        color: #1a3d34 !important;
        border: none !important;
        height: 60px !important;
        font-size: 1.6em !important;
        font-weight: bold !important;
        width: 100% !important;
    }

    /* Smartphone Anpassung */
    @media (max-width: 600px) {
        .header-flex { flex-direction: column; gap: 10px; }
        .info-box-styled, .rsi-box-styled { width: 100%; text-align: center; }
    }
    
    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# SUCHE
search = st.text_input("Aktie / ISIN / WKN suchen:", placeholder="Tippen...")
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
    # Batch Download (Verhindert Fehler bei mehreren Aktien)
    all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)

    for i, ticker in enumerate(st.session_state.watchlist):
        bg_color = OUTER_COLORS[i % len(OUTER_COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")
        
        # --- STUFE 1: ÄUSSERER CONTAINER (FARBIG) ---
        with st.container(border=True):
            # Dieser Anchor identifiziert den gesamten Block für das CSS
            st.markdown(f'<div class="outer-anchor" id="out-{safe_id}"></div>', unsafe_allow_html=True)
            st.markdown(f"""
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#out-{safe_id}) {{
                    background-color: {bg_color} !important;
                }}
                </style>
                """, unsafe_allow_html=True)
            
            try:
                # Daten extrahieren
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    eval_txt = "Überkauft" if rsi_v > 70 else ("Überverkauft" if rsi_v < 30 else "Neutral")

                    # HEADER BEREICH (INFO & RSI)
                    st.markdown(f"""
                        <div class="header-flex">
                            <div class="info-box-styled">{ticker} : {price:.2f}</div>
                            <div class="rsi-box-styled">RSI (14): {rsi_v:.2f} - {eval_txt}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # --- STUFE 2: CHART CONTAINER (PFIRSICH) ---
                    with st.container(border=True):
                        st.markdown(f'<div class="chart-anchor"></div>', unsafe_allow_html=True)
                        fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                        fig.add_hline(y=70, line_dash="dash", line_color="red")
                        fig.add_hline(y=30, line_dash="dash", line_color="green")
                        fig.update_layout(
                            height=220, margin=dict(l=10,r=10,t=10,b=10),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', # Nimmt Pfirsich an
                            font=dict(color="#1a3d5e", size=11),
                            xaxis=dict(showgrid=False), yaxis=dict(range=[0,100], showgrid=False)
                        )
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # --- STUFE 3: BUTTON CONTAINER (HELLGRÜN) ---
                    with st.container(border=True):
                        st.markdown(f'<div class="button-anchor"></div>', unsafe_allow_html=True)
                        if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker, use_container_width=True):
                            st.session_state.watchlist.remove(ticker)
                            remove_from_db(ticker)
                            st.rerun()

            except: continue
