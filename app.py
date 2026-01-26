import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- KONFIGURATION ---
# Verschiedene Hintergrundfarben für die Module
COLORS = ["#1e3b4f", "#2b306b", "#1e4f3e", "#3e1e4f", "#4f3a1e"]

# --- FUNKTIONEN ---
def trigger_rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

def load_from_secrets():
    """Lädt die Master-Liste bei jedem Reboot frisch aus den Secrets"""
    try:
        # Erwartet in den Streamlit Cloud Secrets: START_STOCKS = "AAPL,TSLA,MSFT"
        secret_string = st.secrets.get("START_STOCKS", "AAPL")
        return [s.strip() for s in secret_string.split(",") if s.strip()]
    except:
        return ["AAPL"]

@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)

@st.cache_data(ttl=3600)
def get_isin(ticker):
    """Holt die ISIN (gecached, da dies langsam sein kann)"""
    try:
        t_obj = yf.Ticker(ticker)
        return t_obj.isin if t_obj.isin else "N/A"
    except:
        return "N/A"

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Master Tracker", layout="wide")

# CSS: Laptop zentriert, Mobile voll, 3-Stufen-Modul Design
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    
    /* Laptop-Layout zentrieren (850px) */
    @media (min-width: 768px) {
        .main .block-container { max-width: 850px; margin: auto; }
    }

    /* Das geschlossene 3-Stufen-Modul */
    .stock-module {
        padding: 25px;
        border-radius: 20px;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    /* Stufe 1: Header (Name, ISIN, Preis links | Bubble rechts) */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        flex-wrap: wrap;
    }
    .header-left { display: flex; align-items: baseline; gap: 15px; }
    .header-name { font-size: 2.4em; font-weight: bold; }
    .header-isin { font-size: 1em; color: #bbb; }
    .header-price { font-size: 1.8em; font-weight: bold; }

    .rsi-bubble {
        padding: 12px 24px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 1.2em;
        text-align: center;
        border: 2px solid;
    }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.15); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.15); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.15); }

    /* Stufe 3: Button am unteren Ende des Moduls */
    div.stButton > button {
        background-color: rgba(255,255,255,0.08) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px;
        width: 100%;
        margin-top: 15px;
        height: 45px;
    }
    div.stButton > button:hover {
        background-color: #ff4e4e !important;
        border-color: #ff4e4e !important;
    }
    
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# BEIM START: Immer Liste aus Secrets laden
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_from_secrets()

# SIDEBAR ZUM KOPIEREN
with st.sidebar:
    st.header("📋 Liste Verwalten")
    st.write("Inhalt deiner aktuellen Secrets:")
    current_list_str = ",".join(st.session_state.watchlist)
    st.text_area("Kopieren & in START_STOCKS speichern:", value=current_list_str, height=100)
    if st.button("🔄 Jetzt aus Secrets aktualisieren"):
        st.session_state.watchlist = load_from_secrets()
        trigger_rerun()

st.title("📈 RSI Master Tracker")

# SUCHE
search = st.text_input("Aktie hinzufügen...", placeholder="Name, ISIN oder Symbol...")
if len(search) > 1:
    res = yf.Search(search, max_results=5).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
        sel = st.selectbox("Ergebnis wählen:", options.keys())
        if st.button("➕ Zur Liste hinzufügen", use_container_width=True):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                trigger_rerun()

st.divider()

# ANZEIGE DER MODULE
if st.session_state.watchlist:
    # Batch Download für Schnelligkeit
    all_data = fetch_data(st.session_state.watchlist)
    
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            mod_color = COLORS[i % len(COLORS)]
            isin = get_isin(ticker)
            
            # Daten-Extraktion für den RSI Chart
            df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
            
            if not df.empty:
                rsi_val = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]
                
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "Kaufzone" if rsi_val < 30 else "Verkaufzone" if rsi_val > 70 else "Neutral"

                # DAS GESCHLOSSENE MODUL (3 STUFEN)
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
                            RSI (14): {rsi_val:.2f}<br>{txt}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # STUFE 2: Chart (Mittig im Modul)
                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=180, margin=dict(l=0,r=0,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', 
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                # STUFE 3: Button (Unten im Modul)
                if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker):
                    st.session_state.watchlist.remove(ticker)
                    trigger_rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
        except: continue
