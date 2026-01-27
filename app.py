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

def get_currency_and_name(ticker):
    euro_exchanges = [".TG", ".DE", ".F", ".BE", ".MU", ".DU", ".HA", ".ZE"]
    currency = "€" if any(ticker.upper().endswith(ext) for ext in euro_exchanges) else "$"
    try:
        t = yf.Ticker(ticker)
        name = t.info.get('longName') or t.info.get('shortName') or ticker
    except:
        name = ticker
    return name.upper(), currency

def calc_rsi(series, period=5):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker", layout="wide")

# CSS: STRENGE ZENTRIERUNG & MODUL-DESIGN
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    
    /* Laptop-Zentrierung auf exakt 700px Breite */
    @media (min-width: 1024px) {
        section[data-testid="stAppViewBlockContainer"] {
            max-width: 700px !important;
            margin: auto !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

    /* Das Modul-Gefäß (Umschließt Header, Chart und Button) */
    .stock-container {
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 40px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        border: 1px solid rgba(255,255,255,0.1);
    }

    /* Header: Alles in einer Zeile */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .header-left {
        display: flex;
        align-items: baseline;
        gap: 10px;
        font-weight: bold;
        font-size: 1.1em;
    }

    .header-price { color: #00ff88; }

    .rsi-bubble {
        padding: 6px 12px;
        border-radius: 10px;
        font-weight: bold;
        text-align: center;
        border: 2px solid;
        font-size: 0.85em;
    }
    
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }
    
    /* Buttons einpassen */
    div.stButton > button {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 10px;
        width: 100%;
        font-weight: bold;
        height: 40px;
    }
    div.stButton > button:hover { background-color: #ff4e4e !important; border-color: #ff4e4e !important; }
    
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# Start-Liste laden
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

# SIDEBAR BACKUP
with st.sidebar:
    st.header("⚙️ Verwaltung")
    current_list_str = ",".join(st.session_state.watchlist)
    st.text_area("Master-Liste:", value=current_list_str, height=120)
    if st.button("🔄 Reset aus Secrets"):
        st.session_state.watchlist = load_from_secrets()
        st.cache_data.clear()
        trigger_rerun()

st.title("📈 RSI Tracker")

# SUCHE
search = st.text_input("Aktie hinzufügen...", placeholder="z.B. Tesla, Apple...")
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
    except: st.error("Suche nicht verfügbar.")

st.divider()

# ANZEIGE DER MODULE
if st.session_state.watchlist:
    all_data = fetch_stock_data(st.session_state.watchlist)
    
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            mod_color = COLORS[i % len(COLORS)]
            co_name, currency = get_currency_and_name(ticker)
            
            df_full = all_data['Close'][ticker].dropna() if len(st.session_state.watchlist) > 1 else all_data['Close'].dropna()
            
            if not df_full.empty:
                rsi_series = calc_rsi(df_full, period=5)
                rsi_recent = rsi_series.tail(5)
                current_price = df_full.iloc[-1]
                rsi_val = rsi_recent.iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "KAUFZONE" if rsi_val < 30 else "VERKAUFZONE" if rsi_val > 70 else "NEUTRAL"

                # HIER STARTET DAS MODUL-GEFÄSS
                st.markdown(f'<div class="stock-container" style="background-color: {mod_color};">', unsafe_allow_html=True)
                
                # STUFE 1: Header
                st.markdown(f"""
                <div class="module-header">
                    <div class="header-left">
                        <span>{co_name}:</span><span>{ticker}</span>
                        <span class="header-price">{current_price:.2f} {currency}</span>
                    </div>
                    <div class="rsi-bubble {cl}">RSI: {rsi_val:.2f}<br>{txt}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # STUFE 2: Chart (Mitte)
                fig = go.Figure(go.Scatter(
                    x=rsi_recent.index, y=rsi_recent, mode='lines+markers', 
                    line=dict(color='white', width=4), marker=dict(size=10)
                ))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=160, margin=dict(l=0,r=0,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', 
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False, tickformat="%d.%m"), yaxis=dict(range=[0, 100], showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                # STUFE 3: Button (Unten)
                if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker):
                    st.session_state.watchlist.remove(ticker)
                    trigger_rerun()
                
                # MODUL-GEFÄSS ENDE
                st.markdown('</div>', unsafe_allow_html=True)
        except: continue
