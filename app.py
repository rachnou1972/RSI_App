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
    try:
        secret_string = st.secrets.get("START_STOCKS", "TL0.TG,APC.TG")
        return [s.strip() for s in secret_string.split(",") if s.strip()]
    except:
        return ["TL0.TG"]

@st.cache_data(ttl=300)
def get_euro_rate():
    """Holt den aktuellen Wechselkurs USD -> EUR"""
    try:
        data = yf.download("USDEUR=X", period="1d", interval="1m", progress=False)
        return data['Close'].iloc[-1]
    except:
        return 0.95

@st.cache_data(ttl=60)
def fetch_live_data(tickers):
    if not tickers: return pd.DataFrame()
    data = yf.download(tickers, period="6mo", interval="1d", progress=False)
    return data.ffill()

@st.cache_data(ttl=3600)
def get_stock_details(ticker):
    """Holt Name, ISIN und Währung"""
    try:
        t = yf.Ticker(ticker)
        name = t.info.get('longName') or t.info.get('shortName') or ticker
        currency = t.info.get('currency', 'EUR')
        isin = t.isin if hasattr(t, 'isin') else "N/A"
        return name.upper(), currency, isin
    except:
        return ticker.upper(), 'EUR', 'N/A'

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker", layout="wide")

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
    st.header("⚙️ Verwaltung")
    st.write("Aktuelle Liste für Secrets:")
    st.code(",".join(st.session_state.watchlist))
    if st.button("🔄 Reset / Secrets laden"):
        st.session_state.watchlist = load_from_secrets()
        st.cache_data.clear()
        trigger_rerun()

st.title("📈 RSI Tracker (Euro Preise)")

# UPDATE BUTTON
if st.button("🔄 Marktdaten jetzt aktualisieren", use_container_width=True):
    st.cache_data.clear()
    trigger_rerun()

# --- SUCHE (Offen für alle Börsen) ---
search = st.text_input("Aktie suchen (Name, ISIN oder Symbol)...", placeholder="z.B. Tesla, Apple, Allianz...")
if len(search) > 1:
    res = yf.Search(search, max_results=10).quotes
    if res:
        options = {}
        for r in res:
            sym = r.get('symbol')
            name = r.get('shortname', 'Info')
            exch = r.get('exchDisp', 'Börse')
            label = f"{name} ({sym}) - Börse: {exch}"
            options[label] = sym
            
        sel = st.selectbox("Wähle das passende Symbol:", options.keys())
        if st.button("➕ Hinzufügen"):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# --- ANZEIGE ---
if st.session_state.watchlist:
    all_data = fetch_live_data(st.session_state.watchlist)
    usd_to_eur = get_euro_rate()
    
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            mod_color = COLORS[i % len(COLORS)]
            co_name, currency, isin = get_stock_details(ticker)
            
            # Daten-Extraktion
            if len(st.session_state.watchlist) > 1:
                col_data = all_data['Close'][ticker].dropna()
            else:
                col_data = all_data['Close'].dropna()
            
            if not col_data.empty:
                raw_price = col_data.iloc[-1]
                # Umrechnung falls nicht in Euro (z.B. US-Aktie gewählt)
                current_price = raw_price * usd_to_eur if currency == 'USD' else raw_price
                
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
