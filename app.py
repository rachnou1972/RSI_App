import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- KONFIGURATION ---
COLORS = ["#1e3b4f", "#2b306b", "#1e4f3e", "#3e1e4f", "#4f3a1e"]

# --- FUNKTIONEN ---
def trigger_rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

def load_from_secrets():
    """Lädt die Master-Liste aus den Secrets"""
    try:
        secret_string = st.secrets.get("START_STOCKS", "AAPL,TSLA")
        return [s.strip() for s in secret_string.split(",") if s.strip()]
    except:
        return ["AAPL"]

@st.cache_data(ttl=60) # Kurzes Caching für Performance, aber schnelle Updates
def fetch_live_data(tickers):
    if not tickers: return pd.DataFrame()
    # Wir laden 3 Monate Daten, um den RSI (14) berechnen zu können
    return yf.download(tickers, period="3mo", interval="1d", progress=False)

@st.cache_data(ttl=3600)
def get_company_info(ticker):
    """Holt Firmenname und ISIN (länger gecached, da stabil)"""
    try:
        t = yf.Ticker(ticker)
        name = t.info.get('longName', ticker)
        isin = t.isin if hasattr(t, 'isin') else "N/A"
        return name.upper(), isin
    except:
        return ticker.upper(), "N/A"

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Pro Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    @media (min-width: 768px) { .main .block-container { max-width: 850px; margin: auto; } }
    .stock-module { padding: 25px; border-radius: 20px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; }
    .header-left { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
    .header-main-text { font-size: 1.8em; font-weight: bold; } /* Firmenname: Symbol Preis */
    .header-isin { font-size: 0.9em; color: #bbb; }
    .rsi-bubble { padding: 12px 20px; border-radius: 12px; font-weight: bold; font-size: 1.1em; text-align: center; border: 2px solid; }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.15); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.15); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.15); }
    div.stButton > button { background-color: rgba(255,255,255,0.1) !important; color: white !important; border-radius: 12px; width: 100%; margin-top: 15px; height: 45px; }
    div.stButton > button:hover { background-color: #ff4e4e !important; }
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

# SIDEBAR BACKUP
with st.sidebar:
    st.header("📋 Master-Liste")
    current_list_str = ",".join(st.session_state.watchlist)
    st.text_area("Kopieren für START_STOCKS:", value=current_list_str, height=100)
    if st.button("🔄 Aus Secrets neu laden"):
        st.session_state.watchlist = load_from_secrets()
        trigger_rerun()

st.title("📈 RSI Tracker Live")

# SUCHE
search = st.text_input("Aktie hinzufügen...", placeholder="Name, ISIN oder Symbol...")
if len(search) > 1:
    res = yf.Search(search, max_results=5).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
        sel = st.selectbox("Ergebnis wählen:", options.keys())
        if st.button("➕ Hinzufügen", use_container_width=True):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                trigger_rerun()

st.divider()

# ANZEIGE DER MODULE
if st.session_state.watchlist:
    # Zwingt Update: Wir holen die Daten jedes Mal neu (ttl=60 im Cache)
    all_data = fetch_live_data(st.session_state.watchlist)
    
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            mod_color = COLORS[i % len(COLORS)]
            co_name, isin = get_company_info(ticker)
            
            df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
            
            if not df.empty:
                rsi_val = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "KAUFEN" if rsi_val < 30 else "VERKAUFEN" if rsi_val > 70 else "NEUTRAL"

                # 3-STUFEN-MODUL
                st.markdown(f"""
                <div class="stock-module" style="background-color: {mod_color};">
                    <div class="module-header">
                        <div class="header-left">
                            <span class="header-main-text">{co_name}: {ticker} {price:.2f} €</span>
                            <span class="header-isin">ISIN: {isin}</span>
                        </div>
                        <div class="rsi-bubble {cl}">
                            RSI: {rsi_val:.2f}<br>{txt}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Chart
                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=180, margin=dict(l=0,r=0,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', 
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker):
                    st.session_state.watchlist.remove(ticker)
                    trigger_rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
        except: continue
