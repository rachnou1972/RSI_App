import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- DATEN-MANAGEMENT (Master-Liste aus Secrets) ---
def load_master_watchlist():
    """Lädt die Liste aus den Streamlit Secrets (Variable: START_STOCKS)"""
    try:
        # Erwartet einen String wie: "AAPL,TSLA,MSFT"
        secret_list = st.secrets.get("START_STOCKS", "AAPL")
        return [s.strip() for s in secret_list.split(",") if s.strip()]
    except:
        return ["AAPL"]

def trigger_rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

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
st.set_page_config(page_title="RSI Master Tracker", layout="wide")

# Kräftige Farben für die Module
COLORS = ["#1e3b4f", "#2b306b", "#1e4f3e", "#3e1e4f", "#4f3a1e"]

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
        box-shadow: 0 8px 25px rgba(0,0,0,0.5);
    }

    /* Stufe 1: Header (Name, ISIN, Preis, Bubble) */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    .header-left { display: flex; align-items: baseline; gap: 15px; }
    .header-name { font-size: 2.2em; font-weight: bold; }
    .header-isin { font-size: 0.9em; color: #ccc; }
    .header-price { font-size: 1.8em; font-weight: bold; }

    .rsi-bubble {
        padding: 8px 18px;
        border-radius: 50px;
        font-weight: bold;
        font-size: 1.1em;
        border: 2px solid;
    }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.15); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.15); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.15); }

    /* Stufe 3: Button */
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

# Watchlist initialisieren
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_master_watchlist()

# SIDEBAR FÜR BACKUP (Damit du die Liste für deine Secrets hast)
with st.sidebar:
    st.header("📋 Master-Liste")
    st.write("Kopiere diesen Text für deine Streamlit Secrets (START_STOCKS):")
    current_list_str = ",".join(st.session_state.watchlist)
    st.text_area("Copy-Paste:", value=current_list_str, height=100)
    if st.button("🔄 Auf Master-Liste zurücksetzen"):
        st.session_state.watchlist = load_master_watchlist()
        trigger_rerun()

st.title("📈 RSI Master Tracker")

# --- SUCHE ---
search = st.text_input("Aktie hinzufügen (Name, ISIN, Symbol)...")
if len(search) > 1:
    res = yf.Search(search, max_results=5).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
        sel = st.selectbox("Wähle:", options.keys())
        if st.button("➕ Hinzufügen", use_container_width=True):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
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
            
            # Daten-Extraktion
            if len(st.session_state.watchlist) > 1:
                df = all_data.xs(ticker, axis=1, level=1)
            else:
                df = all_data
            
            if not df.empty:
                rsi_val = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "Kaufzone" if rsi_val < 30 else "Verkaufzone" if rsi_val > 70 else "Neutral"

                # 3-STUFEN-MODUL
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
                
                # STUFE 2: Chart
                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', 
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                # STUFE 3: Button
                if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker):
                    st.session_state.watchlist.remove(ticker)
                    trigger_rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
        except: continue
