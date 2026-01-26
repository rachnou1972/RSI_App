import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_module.db"
# Kräftige Modul-Farben
COLORS = ["#1e3b4f", "#2b306b", "#1e4f3e", "#3e1e4f", "#4f3a1e"]

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
        try:
            secret_list = st.secrets.get("START_STOCKS", "")
            if secret_list:
                data = [s.strip() for s in secret_list.split(",") if s.strip()]
                for s in data: add_to_db(s)
        except: data = ["AAPL"]
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

def trigger_rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

# --- SICHERHEIT ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Trader Login")
        try: pw = st.secrets["MY_PASSWORD"]
        except: st.error("Secrets fehlen!"); st.stop()
        u_input = st.text_input("Passwort", type="password")
        if st.button("Anmelden", use_container_width=True):
            if user_input == pw:
                st.session_state.password_correct = True
                trigger_rerun()
            else: st.error("Falsch!")
        return False
    return True

if not check_password(): st.stop()

# --- DATEN LOGIK ---
@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker", layout="wide")
init_db()

# CSS für das 3-Stufen-Modul
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    
    @media (min-width: 768px) {
        .main .block-container { max-width: 850px; margin: auto; }
    }

    /* Das gesamte Modul-Element */
    .stock-module {
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 30px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.4);
    }

    /* Stufe 1: Header */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    .header-left { display: flex; align-items: baseline; gap: 15px; }
    .header-name { font-size: 2.2em; font-weight: bold; }
    .header-isin { font-size: 0.9em; color: #ccc; }
    .header-price { font-size: 1.8em; font-weight: bold; color: #fff; }

    /* Die RSI Bubble */
    .rsi-bubble {
        padding: 10px 20px;
        border-radius: 50px;
        font-weight: bold;
        font-size: 1.2em;
        border: 2px solid;
    }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.15); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.15); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.15); }

    /* Button Styling */
    div.stButton > button {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        border-radius: 10px;
        width: 100%;
        margin-top: 10px;
    }
    div.stButton > button:hover {
        background-color: #ff4e4e !important;
        border-color: #ff4e4e !important;
    }
    
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

with st.sidebar:
    st.header("⚙️ Menü")
    current_list = ",".join(st.session_state.watchlist)
    st.text_area("Backup für Secrets:", value=current_list, height=100)
    if st.button("Abmelden"):
        st.session_state.clear()
        trigger_rerun()

st.title("📈 RSI Tracker")

# SUCHE
search = st.text_input("Suchen (Name, ISIN, Symbol)...")
if len(search) > 1:
    res = yf.Search(search, max_results=5).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')}) - {r.get('exchDisp')}": r.get('symbol') for r in res}
        sel = st.selectbox("Wähle:", options.keys())
        if st.button("➕ Hinzufügen", use_container_width=True):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                add_to_db(sym)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# --- ANZEIGE DER MODULE ---
if st.session_state.watchlist:
    all_data = fetch_data(st.session_state.watchlist)
    
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            mod_color = COLORS[i % len(COLORS)]
            t_info = yf.Ticker(ticker)
            isin = t_info.isin if hasattr(t_info, 'isin') else "N/A"
            
            df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
            
            if not df.empty:
                rsi_val = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "Kaufzone" if rsi_val < 30 else "Verkaufzone" if rsi_val > 70 else "Neutral"

                # HIER STARTET DAS MODUL (HTML)
                st.markdown(f"""
                <div class="stock-module" style="background-color: {mod_color};">
                    <!-- STUFE 1: Header -->
                    <div class="module-header">
                        <div class="header-left">
                            <span class="header-name">{ticker}</span>
                            <span class="header-isin">ISIN: {isin}</span>
                            <span class="header-price">{price:.2f}</span>
                        </div>
                        <div class="rsi-bubble {cl}">
                            RSI: {rsi_val:.2f} - {txt}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # STUFE 2: Chart (Mitte)
                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', 
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                # STUFE 3: Button (Unten) - Wir stylen ihn so, dass er ins Modul passt
                if st.button(f"🗑️ {ticker} löschen", key="del_"+ticker, use_container_width=True):
                    st.session_state.watchlist.remove(ticker)
                    remove_from_db(ticker)
                    st.cache_data.clear()
                    trigger_rerun()
                
                # MODUL ENDE
                st.markdown("</div>", unsafe_allow_html=True)
        except: continue
