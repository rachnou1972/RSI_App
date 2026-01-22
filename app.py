import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK ---
DB_NAME = "watchlist_final_pro.db"
# Kräftige Modul-Farben (Blau, Dunkelgrün, Weinrot, Violett, Petrol)
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
st.set_page_config(page_title="RSI Tracker Ultimate", layout="wide")
init_db()

# --- BASIS CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117 !important; }
    
    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* Diese Regeln bereiten die Streamlit-Container auf die Farbinjektion vor */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 40px !important;
        border: none !important;
        margin-bottom: 40px !important;
        overflow: hidden !important;
    }

    /* Header Design */
    .custom-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        margin-bottom: 15px;
    }
    .info-box {
        background-color: #d1e8ff; 
        padding: 10px 15px;
        border-radius: 5px;
        color: #ff0000 !important;
        font-weight: bold;
        font-size: 1.1em;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .rsi-box {
        background-color: #ffb400; 
        padding: 10px 15px;
        border-radius: 5px;
        color: black !important;
        font-weight: bold;
        font-size: 1.2em;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }

    /* Chart & Button Container Styling */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-marker) {
        background-color: #f7cbb4 !important; /* Pfirsich */
        padding: 10px !important;
        border-radius: 20px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.button-marker) {
        background-color: #c4f3ce !important; /* Hellgrün */
        padding: 0px !important;
        border-radius: 15px !important;
    }

    /* Button Fix */
    div.stButton > button {
        background-color: transparent !important;
        color: #1a3d34 !important;
        border: none !important;
        height: 60px !important;
        width: 100% !important;
        font-size: 1.5em !important;
        font-weight: bold !important;
    }
    
    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Suchen (Name/ISIN/Ticker):", placeholder="Tippen zum Suchen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Auswählen:", opts.keys())
            if st.button("➕ Hinzufügen", use_container_width=True):
                s = opts[sel]
                if s not in st.session_state.watchlist:
                    st.session_state.watchlist.append(s)
                    add_to_db(s)
                    st.rerun()
    except: pass

st.divider()

# --- ANZEIGE ---
if st.session_state.watchlist:
    # Daten laden
    try:
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        color = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")
        
        # --- FARBINJEKTION: DAS ERZWINGT DEN HINTERGRUND ---
        # Wir suchen den äußeren Wrapper und färben ihn ein.
        st.markdown(f"""
            <style>
            div[data-testid="stVerticalBlockBorderWrapper"]:has(#outer-{safe_id}) {{
                background-color: {color} !important;
                padding: 25px !important;
            }}
            /* Entferne Abstände zwischen den Stufen */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(#outer-{safe_id}) div[data-testid="stVerticalBlock"] {{
                gap: 15px !important;
            }}
            </style>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            # Der Marker für den äußeren Block
            st.markdown(f'<div id="outer-{safe_id}" class="outer-marker"></div>', unsafe_allow_html=True)
            
            try:
                # Daten Extraktion
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                
                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    # ISIN/Name Suche
                    t_info = yf.Ticker(ticker)
                    display_name = t_info.info.get('shortName', ticker)
                    
                    # STUFE 1: HEADER
                    st.markdown(f"""
                        <div class="custom-header-row">
                            <div class="info-box">{ticker} : {display_name} | {price:.2f}</div>
                            <div class="rsi-box">RSI (14): {rsi_v:.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART (In Pfirsich Box)
                    with st.container(border=True):
                        st.markdown('<div class="chart-marker"></div>', unsafe_allow_html=True)
                        fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                        fig.add_hline(y=70, line_dash="dash", line_color="red")
                        fig.add_hline(y=30, line_dash="dash", line_color="green")
                        fig.update_layout(
                            height=220, margin=dict(l=10,r=10,t=10,b=10),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#1a3d5e", size=12),
                            xaxis=dict(showgrid=False), yaxis=dict(range=[0,100], showgrid=False)
                        )
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # STUFE 3: BUTTON (In Grün Box)
                    with st.container(border=True):
                        st.markdown('<div class="button-marker"></div>', unsafe_allow_html=True)
                        if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker, use_container_width=True):
                            st.session_state.watchlist.remove(ticker)
                            remove_from_db(ticker)
                            st.rerun()
                
            except Exception as e:
                st.error(f"Fehler bei {ticker}")
