import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- KONFIGURATION ---
COLORS = ["#1e3b4f", "#2b306b", "#1e4f3e", "#3e1e4f", "#4f3a1e"]

# --- FUNKTIONEN ---
def trigger_rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

def load_from_secrets():
    try:
        # Standard: Gettex-Ticker für Tesla (TL0.TG) und Apple (APC.TG)
        s_string = st.secrets.get("START_STOCKS", "TL0.TG,APC.TG")
        return [s.strip() for s in s_string.split(",") if s.strip()]
    except:
        return ["TL0.TG"]

@st.cache_data(ttl=30)
def fetch_precise_price(ticker_symbol):
    """Versucht den absolut aktuellsten Preis zu finden"""
    try:
        t = yf.Ticker(ticker_symbol)
        # Erstversuch: Schneller Preisabruf
        fast_price = t.fast_info.get('lastPrice')
        if fast_price:
            return fast_price
        # Zweitversuch: Historie
        hist = t.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
    except:
        return None

@st.cache_data(ttl=300)
def fetch_chart_data(ticker_symbol):
    """Lädt die Kurs-Historie für den RSI-Chart"""
    try:
        data = yf.download(ticker_symbol, period="6mo", interval="1d", progress=False)
        return data.ffill()
    except:
        return pd.DataFrame()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Gettex Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    @media (min-width: 768px) { .main .block-container { max-width: 850px; margin: auto; } }
    .stock-module { padding: 25px; border-radius: 20px; margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .header-main-text { font-size: 1.5em; font-weight: bold; }
    .rsi-bubble { padding: 10px 15px; border-radius: 12px; font-weight: bold; text-align: center; border: 2px solid; min-width: 140px; }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }
    div.stButton > button { background-color: #4e8cff !important; color: white !important; border-radius: 10px; font-weight: bold; height: 45px; }
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

st.title("📈 RSI Tracker (Gettex / Euro)")
st.caption("Hinweis: Kostenlose Daten sind ca. 15 Min. verzögert zum Echtzeit-Broker.")

# UPDATE BUTTON
if st.button("🔄 Alle Preise jetzt aktualisieren", use_container_width=True):
    st.cache_data.clear()
    trigger_rerun()

# SUCHE
search = st.text_input("Aktie suchen (Tipp: Wähle Ergebnisse mit '.TG' am Ende)", placeholder="z.B. Tesla, Apple...")
if len(search) > 1:
    res = yf.Search(search, max_results=10).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')}) - {r.get('exchDisp')}": r.get('symbol') for r in res}
        sel = st.selectbox("Welche Aktie möchtest du hinzufügen?", options.keys())
        if st.button("➕ Hinzufügen"):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# ANZEIGE
for i, ticker in enumerate(st.session_state.watchlist):
    try:
        with st.spinner(f"Lade {ticker}..."):
            price = fetch_precise_price(ticker)
            df = fetch_chart_data(ticker)
            mod_color = COLORS[i % len(COLORS)]
            
            if price and not df.empty:
                rsi_series = calc_rsi(df['Close'])
                rsi_val = rsi_series.iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "KAUFEN" if rsi_val < 30 else "VERKAUFEN" if rsi_val > 70 else "NEUTRAL"

                st.markdown(f"""
                <div class="stock-module" style="background-color: {mod_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <div class="header-main-text">{ticker}: {price:.2f} €</div>
                        <div class="rsi-bubble {cl}">RSI: {rsi_val:.2f}<br>{txt}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Plotly Chart
                fig = go.Figure(go.Scatter(x=df.index, y=rsi_series, line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=160, margin=dict(l=0,r=0,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', 
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker):
                    st.session_state.watchlist.remove(ticker)
                    trigger_rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    except:
        st.error(f"Fehler bei {ticker}")
