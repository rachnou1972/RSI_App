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
    """Lädt die Master-Liste aus den Secrets (START_STOCKS)"""
    try:
        secret_string = st.secrets.get("START_STOCKS", "TL0.TG,APC.TG")
        return [s.strip() for s in secret_string.split(",") if s.strip()]
    except:
        return ["TL0.TG"]

@st.cache_data(ttl=60)
def fetch_live_data(tickers):
    if not tickers: return pd.DataFrame()
    data = yf.download(tickers, period="6mo", interval="1d", progress=False)
    return data.ffill()

@st.cache_data(ttl=3600)
def get_stock_details(ticker):
    """Holt Firmenname und ISIN"""
    try:
        t = yf.Ticker(ticker)
        name = t.info.get('longName') or t.info.get('shortName') or ticker
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
st.set_page_config(page_title="RSI Gettex Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    @media (min-width: 768px) { .main .block-container { max-width: 850px; margin: auto; } }
    
    .stock-module { padding: 25px; border-radius: 20px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; }
    .header-left { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; text-align: left; }
    .header-main-text { font-size: 1.5em; font-weight: bold; line-height: 1.2; }
    
    .rsi-bubble { padding: 10px 20px; border-radius: 12px; font-weight: bold; font-size: 1.1em; text-align: center; border: 2px solid; min-width: 140px; }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }
    
    div.stButton > button { background-color: #4e8cff !important; color: white !important; border-radius: 12px; width: 100%; font-weight: bold; height: 45px; border: none; }
    .btn-del > div.stButton > button { background-color: rgba(255,255,255,0.1) !important; margin-top: 15px; border: 1px solid rgba(255,255,255,0.2) !important; }
    .btn-del > div.stButton > button:hover { background-color: #ff4e4e !important; }
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

# SIDEBAR
with st.sidebar:
    st.header("📋 Gettex-Watchlist")
    st.info("Suche filtert automatisch auf Gettex (.TG) für finanzen.net zero Kurse.")
    st.code(",".join(st.session_state.watchlist))
    if st.button("🔄 Reset / Secrets laden"):
        st.session_state.watchlist = load_from_secrets()
        st.cache_data.clear()
        trigger_rerun()

st.title("📈 RSI Tracker (Nur Gettex / Euro)")

# UPDATE BUTTON
if st.button("🔄 Marktdaten aktualisieren", use_container_width=True):
    st.cache_data.clear()
    trigger_rerun()

# --- SUCHE (Gefiltert auf Gettex) ---
search = st.text_input("Aktie auf Gettex suchen (Name oder ISIN)...", placeholder="z.B. Tesla, Apple, Allianz...")
if len(search) > 1:
    res = yf.Search(search, max_results=20).quotes
    if res:
        # FILTER: Nur Ticker, die auf .TG enden (Gettex)
        gettex_options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') 
                          for r in res if str(r.get('symbol')).endswith('.TG')}
        
        if gettex_options:
            sel = st.selectbox("Gefundene Gettex-Aktien:", gettex_options.keys())
            if st.button("➕ Zur Liste hinzufügen"):
                sym = gettex_options[sel]
                if sym not in st.session_state.watchlist:
                    st.session_state.watchlist.append(sym)
                    st.cache_data.clear()
                    trigger_rerun()
        else:
            st.warning("Keine Gettex-Kurse (.TG) für diesen Suchbegriff gefunden. Probiere es mit der ISIN.")

st.divider()

# --- ANZEIGE DER MODULE ---
if st.session_state.watchlist:
    all_data = fetch_live_data(st.session_state.watchlist)
    
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            mod_color = COLORS[i % len(COLORS)]
            co_name, isin = get_stock_details(ticker)
            
            # Daten-Extraktion
            if len(st.session_state.watchlist) > 1:
                col_data = all_data['Close'][ticker].dropna()
            else:
                col_data = all_data['Close'].dropna()
            
            if not col_data.empty:
                current_price = col_data.iloc[-1]
                rsi_series = calc_rsi(col_data)
                rsi_val = rsi_series.iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "KAUFEN" if rsi_val < 30 else "VERKAUFEN" if rsi_val > 70 else "NEUTRAL"

                # 3-STUFEN-MODUL
                st.markdown(f"""
                <div class="stock-module" style="background-color: {mod_color};">
                    <div class="module-header">
                        <div class="header-left">
                            <span class="header-main-text">{co_name}: {ticker} {current_price:.2f} €</span>
                        </div>
                        <div class="rsi-bubble {cl}">
                            RSI: {rsi_val:.2f}<br>{txt}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Chart
                fig = go.Figure(go.Scatter(x=col_data.index, y=rsi_series, line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=180, margin=dict(l=0,r=0,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', 
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                # Löschen
                st.markdown('<div class="btn-del">', unsafe_allow_html=True)
                if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker):
                    st.session_state.watchlist.remove(ticker)
                    trigger_rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)
        except Exception as e:
            continue
