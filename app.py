import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- AUTOMATISCHES UPDATE ALLE 30 SEKUNDEN ---
st_autorefresh(interval=30 * 1000, key="datarefresh")

# --- KONFIGURATION ---
COLORS = ["#1e3b4f", "#2b306b", "#1e4f3e", "#3e1e4f", "#4f3a1e"]

# --- FUNKTIONEN ---
def trigger_rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

def load_from_secrets():
    try:
        secret_string = st.secrets.get("START_STOCKS", "TL0.TG,AAPL")
        return [s.strip() for s in secret_string.split(",") if s.strip()]
    except:
        return ["TL0.TG"]

@st.cache_data(ttl=25)
def fetch_stock_data(tickers):
    if not tickers: return pd.DataFrame()
    # Wir laden 1 Monat Daten, um den RSI stabil berechnen zu können
    data = yf.download(tickers, period="1mo", interval="1d", progress=False)
    return data.ffill()

@st.cache_data(ttl=3600)
def get_stock_meta(ticker):
    try:
        t = yf.Ticker(ticker)
        name = t.info.get('longName') or ticker
        curr_code = t.info.get('currency', '')
        mapping = {"USD": "$", "EUR": "€", "GBp": "p", "CHF": "Fr"}
        symbol = mapping.get(curr_code, curr_code)
        return name.upper(), symbol
    except:
        return ticker.upper(), ""

def calc_rsi(series, period=5):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI 5-Day Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    @media (min-width: 768px) { .main .block-container { max-width: 850px; margin: auto; } }
    .stock-module { padding: 25px; border-radius: 20px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .header-main-text { font-size: 1.4em; font-weight: bold; }
    .rsi-bubble { padding: 10px 20px; border-radius: 12px; font-weight: bold; text-align: center; border: 2px solid; min-width: 140px; }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }
    div.stButton > button { background-color: #4e8cff !important; color: white !important; border-radius: 12px; width: 100%; font-weight: bold; height: 45px; border: none; }
    .btn-del > div.stButton > button { background-color: rgba(255,255,255,0.1) !important; margin-top: 15px; }
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

st.title("📈 RSI 5-Tage Tracker")

# SUCHE
search = st.text_input("Aktie hinzufügen...", placeholder="Name oder Symbol...")
if search:
    try:
        s_res = yf.Search(search, max_results=5).quotes
        if s_res:
            options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in s_res if r.get('symbol')}
            sel = st.selectbox("Ergebnis wählen:", options.keys())
            if st.button("➕ Hinzufügen"):
                sym = options[sel]
                if sym not in st.session_state.watchlist:
                    st.session_state.watchlist.append(sym)
                    st.cache_data.clear()
                    trigger_rerun()
    except:
        st.error("Suche aktuell nicht verfügbar.")

st.divider()

# ANZEIGE
if st.session_state.watchlist:
    all_data = fetch_stock_data(st.session_state.watchlist)
    
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            mod_color = COLORS[i % len(COLORS)]
            co_name, currency_symbol = get_stock_meta(ticker)
            
            # Daten extrahieren
            df_full = all_data['Close'][ticker].dropna() if len(st.session_state.watchlist) > 1 else all_data['Close'].dropna()
            
            if not df_full.empty:
                # RSI berechnen (auf Basis der vollen Daten für Stabilität)
                rsi_series = calc_rsi(df_full, period=5)
                
                # Nur die letzten 5 Tage für den Chart und die Anzeige nehmen
                df_recent = df_full.tail(5)
                rsi_recent = rsi_series.tail(5)
                
                current_price = df_recent.iloc[-1]
                rsi_val = rsi_recent.iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "KAUFEN" if rsi_val < 30 else "VERKAUFEN" if rsi_val > 70 else "NEUTRAL"

                st.markdown(f"""
                <div class="stock-module" style="background-color: {mod_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <div class="header-main-text">{co_name}: {ticker} {current_price:.2f} {currency_symbol}</div>
                        <div class="rsi-bubble {cl}">RSI (5): {rsi_val:.2f}<br>{txt}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # CHART: Nur 5 Datenpunkte
                fig = go.Figure(go.Scatter(
                    x=rsi_recent.index, 
                    y=rsi_recent, 
                    mode='lines+markers', # Punkte hinzufügen, damit man die 5 Tage besser sieht
                    line=dict(color='white', width=4),
                    marker=dict(size=8)
                ))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(
                    height=200, margin=dict(l=0,r=0,t=10,b=10), 
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color="white"),
                    xaxis=dict(showgrid=False, tickformat="%d.%b"), 
                    yaxis=dict(range=[0, 100], showgrid=False)
                )
                st.plotly_c
