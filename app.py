import streamlit as st
from yahooquery import Ticker
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
        s_string = st.secrets.get("START_STOCKS", "TL0.TG,APC.TG")
        return [s.strip() for s in s_string.split(",") if s.strip()]
    except:
        return ["TL0.TG"]

@st.cache_data(ttl=60)
def fetch_fast_data(watchlist):
    """Lädt alle Daten für die Watchlist asynchron (blitzschnell)"""
    if not watchlist: return None
    t = Ticker(watchlist, asynchronous=True)
    # 6 Monate Historie
    df = t.history(period="6mo", interval="1d")
    return df

def calc_rsi(series, period=14):
    if len(series) < period: return pd.Series([50]*len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Pro Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    @media (min-width: 768px) { .main .block-container { max-width: 850px; margin: auto; } }
    .stock-module { padding: 25px; border-radius: 20px; margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .header-main-text { font-size: 1.5em; font-weight: bold; }
    .rsi-bubble { padding: 10px 15px; border-radius: 12px; font-weight: bold; text-align: center; border: 2px solid; min-width: 145px; }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }
    div.stButton > button { background-color: #4e8cff !important; color: white !important; border-radius: 10px; font-weight: bold; height: 45px; border: none; }
    .btn-del > div.stButton > button { background-color: rgba(255,255,255,0.1) !important; margin-top: 15px; border: 1px solid rgba(255,255,255,0.2) !important; }
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

# SIDEBAR
with st.sidebar:
    st.header("⚙️ Verwaltung")
    st.code(",".join(st.session_state.watchlist))
    if st.button("🔄 Reset / Secrets laden"):
        st.session_state.watchlist = load_from_secrets()
        st.cache_data.clear()
        trigger_rerun()

st.title("🚀 RSI Tracker (High-Speed)")

# UPDATE BUTTON
if st.button("🔄 Alle Marktdaten aktualisieren", use_container_width=True):
    st.cache_data.clear()
    trigger_rerun()

# SUCHE
search = st.text_input("Aktie suchen (ISIN, Name)...", placeholder="z.B. Tesla, Apple...")
if len(search) > 1:
    t_search = Ticker(search)
    res = t_search.search(limit=8)
    if 'quotes' in res:
        options = {f"{q.get('shortname')} ({q.get('symbol')}) - {q.get('exchDisp')}": q.get('symbol') for q in res['quotes']}
        sel = st.selectbox("Wähle das Symbol:", options.keys())
        if st.button("➕ Hinzufügen"):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# ANZEIGE
if st.session_state.watchlist:
    with st.spinner("Lade Daten über Hochgeschwindigkeits-Schnittstelle..."):
        all_data = fetch_fast_data(st.session_state.watchlist)
    
    if all_data is not None and not all_data.empty:
        # Ticker Info für Namen holen
        t_meta = Ticker(st.session_state.watchlist)
        meta_info = t_meta.price

        for i, ticker in enumerate(st.session_state.watchlist):
            try:
                mod_color = COLORS[i % len(COLORS)]
                
                # Firmenname aus Meta-Daten
                details = meta_info.get(ticker, {})
                name = details.get('longName') or details.get('shortName') or ticker
                
                # Daten aus dem Multi-Index DataFrame holen
                if isinstance(all_data.index, pd.MultiIndex):
                    df = all_data.loc[ticker].dropna()
                else:
                    df = all_data.dropna()

                if not df.empty:
                    # Gettex nutzt 'adjclose' oder 'close'
                    price = df['adjclose'].iloc[-1]
                    rsi_series = calc_rsi(df['adjclose'])
                    rsi_val = rsi_series.iloc[-1]
                    
                    cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                    txt = "KAUFZONE" if rsi_val < 30 else "VERKAUFZONE" if rsi_val > 70 else "NEUTRAL"

                    # 3-STUFEN-MODUL
                    st.markdown(f"""
                    <div class="stock-module" style="background-color: {mod_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <div class="header-main-text">{name.upper()}: {ticker} {price:.2f} €</div>
                            <div class="rsi-bubble {cl}">RSI: {rsi_val:.2f}<br>{txt}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    fig = go.Figure(go.Scatter(x=df.index, y=rsi_series, line=dict(color='white', width=3)))
                    fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                    fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                    fig.update_layout(height=180, margin=dict(l=0,r=0,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', 
                                      plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                      xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    st.markdown('<div class="btn-del">', unsafe_allow_html=True)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker):
                        st.session_state.watchlist.remove(ticker)
                        trigger_rerun()
                    st.markdown('</div></div>', unsafe_allow_html=True)
            except Exception as e:
                continue
