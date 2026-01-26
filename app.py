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
    """Lädt die Liste beim Start zwingend aus den Secrets (START_STOCKS)"""
    try:
        # Holt START_STOCKS = "TL0.TG,APC.TG" aus den Secrets
        secret_string = st.secrets.get("START_STOCKS", "AAPL,TSLA")
        return [s.strip() for s in secret_string.split(",") if s.strip()]
    except:
        return ["AAPL"]

@st.cache_data(ttl=60)
def fetch_stock_data(tickers):
    if not tickers: return pd.DataFrame()
    data = yf.download(tickers, period="6mo", interval="1d", progress=False)
    return data.ffill()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Ultimate Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    
    /* Zentrierung auf Laptop (850px) */
    @media (min-width: 768px) {
        .main .block-container { max-width: 850px; margin: auto; }
    }

    /* Das 3-Stufen-Modul */
    .stock-module {
        padding: 25px;
        border-radius: 20px;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    .header-main-text { font-size: 1.6em; font-weight: bold; }
    
    .rsi-bubble {
        padding: 10px 20px;
        border-radius: 12px;
        font-weight: bold;
        text-align: center;
        border: 2px solid;
        min-width: 140px;
    }
    
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }

    /* Button Design */
    div.stButton > button {
        background-color: #4e8cff !important;
        color: white !important;
        border-radius: 12px;
        width: 100%;
        font-weight: bold;
        height: 45px;
        border: none;
    }
    
    .btn-del > div.stButton > button {
        background-color: rgba(255,255,255,0.1) !important;
        margin-top: 15px;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }
    .btn-del > div.stButton > button:hover { background-color: #ff4e4e !important; }

    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# BEIM START: Liste aus Secrets laden
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

# --- SIDEBAR (DER BEREICH FÜR DIE LISTE / BACKUP) ---
with st.sidebar:
    st.header("📋 Aktuelle Liste (Backup)")
    st.write("Kopiere diesen Text für deine Secrets:")
    current_list_str = ",".join(st.session_state.watchlist)
    st.text_area("In START_STOCKS speichern:", value=current_list_str, height=150)
    
    if st.button("🔄 Liste aus Secrets neu laden"):
        st.session_state.watchlist = load_from_secrets()
        st.cache_data.clear()
        trigger_rerun()

st.title("📈 RSI Tracker")

# MANUELLES UPDATE
if st.button("🔄 Marktdaten aktualisieren", use_container_width=True):
    with st.spinner("Aktualisiere Kurse..."):
        st.cache_data.clear()
        trigger_rerun()

# SUCHE
search = st.text_input("Aktie hinzufügen...", placeholder="Name, ISIN oder Symbol...")
if search:
    try:
        s_res = yf.Search(search, max_results=8).quotes
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

# --- ANZEIGE DER MODULE ---
if st.session_state.watchlist:
    with st.spinner("Hole Marktdaten..."):
        all_data = fetch_stock_data(st.session_state.watchlist)
    
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            mod_color = COLORS[i % len(COLORS)]
            
            # Datenextraktion (Handling für Einzel/Mehrfach Ticker)
            if len(st.session_state.watchlist) > 1:
                df = all_data['Close'][ticker].dropna()
            else:
                df = all_data['Close'].dropna()
            
            if not df.empty:
                # Firmen-Details
                t_info = yf.Ticker(ticker)
                full_name = t_info.info.get('longName') or t_info.info.get('shortName') or ticker
                price = df.iloc[-1]
                
                # RSI
                rsi_series = calc_rsi(df)
                rsi_val = rsi_series.iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "KAUFEN" if rsi_val < 30 else "VERKAUFEN" if rsi_val > 70 else "NEUTRAL"

                # DAS MODUL (STUFE 1: Header | STUFE 2: Chart | STUFE 3: Button)
                st.markdown(f"""
                <div class="stock-module" style="background-color: {mod_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <div class="header-main-text">{full_name.upper()}: {ticker} {price:.2f} €</div>
                        <div class="rsi-bubble {cl}">RSI: {rsi_val:.2f}<br>{txt}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Chart
                fig = go.Figure(go.Scatter(x=df.index, y=rsi_series, line=dict(color='white', width=3)))
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
        except:
            continue
