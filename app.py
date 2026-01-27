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

# CSS: STRENGE ZENTRIERUNG AUF 60% BREITE
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    
    /* Laptop Design: Exakt 60% der Breite und mittig */
    @media (min-width: 1024px) {
        .main .block-container {
            max-width: 60% !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    }

    /* Das 3-Stufen-Modul */
    .stock-module {
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        border: 1px solid rgba(255,255,255,0.05);
    }

    .header-main-text { font-size: 1.3em; font-weight: bold; line-height: 1.2; }
    
    .rsi-bubble {
        padding: 8px 15px;
        border-radius: 12px;
        font-weight: bold;
        text-align: center;
        border: 2px solid;
        min-width: 120px;
        font-size: 0.9em;
    }
    
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }

    div.stButton > button {
        background-color: #4e8cff !important;
        color: white !important;
        border-radius: 12px;
        width: 100%;
        font-weight: bold;
        height: 42px;
        border: none;
    }
    .btn-del > div.stButton > button {
        background-color: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

st.title("📈 RSI Tracker (5D)")

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
            co_name, curr_sym = get_stock_meta(ticker)
            
            # Daten für 5-Tage-Anzeige
            df_full = all_data['Close'][ticker].dropna() if len(st.session_state.watchlist) > 1 else all_data['Close'].dropna()
            
            if not df_full.empty:
                rsi_series = calc_rsi(df_full, period=5)
                df_recent = df_full.tail(5)
                rsi_recent = rsi_series.tail(5)
                
                curr_p = df_recent.iloc[-1]
                rsi_v = rsi_recent.iloc[-1]
                
                cl = "buy" if rsi_v < 30 else "sell" if rsi_v > 70 else "neutral"
                txt = "KAUFZONE" if rsi_v < 30 else "VERKAUFZONE" if rsi_v > 70 else "NEUTRAL"

                # DAS MODUL
                st.markdown(f"""
                <div class="stock-module" style="background-color: {mod_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <div class="header-main-text">{co_name}: {ticker}<br>{curr_p:.2f} {curr_sym}</div>
                        <div class="rsi-bubble {cl}">RSI (5): {rsi_v:.2f}<br>{txt}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # CHART: 5 Tage Verlauf
                fig = go.Figure(go.Scatter(
                    x=rsi_recent.index, 
                    y=rsi_recent, 
                    mode='lines+markers',
                    line=dict(color='white', width=4),
                    marker=dict(size=10, bordercolor="white", borderwidth=1)
                ))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(
                    height=180, margin=dict(l=0,r=0,t=10,b=10), 
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color="white"),
                    xaxis=dict(showgrid=False, tickformat="%d.%m"), 
                    yaxis=dict(range=[0, 100], showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                st.markdown('<div class="btn-del">', unsafe_allow_html=True)
                if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker):
                    st.session_state.watchlist.remove(ticker)
                    trigger_rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)
        except:
            continue
