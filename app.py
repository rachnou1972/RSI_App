import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_ultimate_v60.db"
# Kräftige Modul-Farben (Blau, Grün, Lila, Petrol, Anthrazit)
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#0f766e", "#1e40af"]

# --- BASIS FUNKTIONEN ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def load_watchlist():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT symbol FROM watchlist')
    data = [row[0] for row in c.fetchall()]
    conn.close()
    if not data: return ["AAPL", "TSLA"]
    return data

def add_to_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('INSERT OR REPLACE INTO watchlist VALUES (?)', (symbol,))
        conn.commit()
    except: pass
    conn.close()

def remove_from_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()

def calc_rsi(series, period=14):
    if len(series) < period: return pd.Series([50]*len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker Ultimate", layout="wide")
init_db()

# --- CSS: DAS ERZWINGT DIE FARBEN UND ENTFERNT SCHWARZE LÜCKEN ---
st.markdown("""
    <style>
    /* Hintergrund der gesamten Seite */
    .stApp { background-color: #0e1117 !important; }
    
    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* WICHTIG: Entfernt alle Standard-Abstände (Gaps) von Streamlit innerhalb des Moduls */
    div[data-testid="stVerticalBlock"]:has(> div > div > .module-marker) {
        gap: 0px !important;
    }

    /* Das umschließende farbige Modul-Element */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.module-marker) {
        border-radius: 40px !important;
        padding: 0px !important; /* Padding wird über die inneren Elemente gesteuert */
        margin-bottom: 50px !important;
        border: none !important;
        overflow: hidden !important;
    }

    /* --- STUFE 1: HEADER --- */
    .header-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 30px 25px 20px 25px;
        width: 100%;
    }
    .info-box {
        background-color: #d1e8ff; 
        padding: 10px 20px;
        border-radius: 8px;
        color: #ff0000; /* Ticker in Rot */
        font-weight: bold;
        font-size: 1.2em;
    }
    .rsi-box {
        background-color: #ffb400; 
        padding: 10px 20px;
        border-radius: 8px;
        color: black;
        font-weight: bold;
        font-size: 1.4em;
        border: 2px solid black;
    }

    /* --- STUFE 2: CHART (Pfirsich) --- */
    .chart-container {
        padding: 0 25px 25px 25px; /* Erzeugt den farbigen Rand des Moduls um den Chart */
    }
    .chart-peach-box {
        background-color: #f7cbb4;
        border-radius: 20px;
        padding: 15px;
        border: 1px solid rgba(0,0,0,0.1);
    }

    /* --- STUFE 3: BUTTON (Hellgrün) --- */
    .button-container {
        padding: 0 25px 30px 25px; /* Erzeugt den farbigen Rand um den Button */
    }
    div.stButton > button {
        background-color: #c4f3ce !important; 
        color: #1a3d34 !important;
        border-radius: 15px !important;
        height: 60px !important;
        font-size: 1.6em !important;
        font-weight: bold !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
        width: 100% !important;
    }

    /* Smartphone Optimierung */
    @media (max-width: 600px) {
        .header-section { flex-direction: column; gap: 15px; padding: 20px 15px; }
        .info-box, .rsi-box { width: 100%; text-align: center; }
        div.stButton > button { font-size: 1.3em !important; }
    }
    
    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Aktie / ISIN / WKN suchen:", placeholder="Tippen zum Suchen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Ergebnis wählen:", opts.keys())
            if st.button("➕ Hinzufügen", use_container_width=True):
                s = opts[sel]
                if s not in st.session_state.watchlist:
                    st.session_state.watchlist.append(s)
                    add_to_db(s)
                    st.rerun()
    except: pass

st.divider()

# --- ANZEIGE DER MODULE NACH DEINER ZEICHNUNG ---
if st.session_state.watchlist:
    # Batch Download für Geschwindigkeit
    try:
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.error("Datenfehler.")
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        bg_color = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")
        
        # DER CONTAINER UM ALLES (Das Modul)
        with st.container(border=True):
            # Der Marker und das CSS erzwingen die Hintergrundfarbe des Moduls
            st.markdown(f"""
                <div class="module-marker" id="mark-{safe_id}"></div>
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#mark-{safe_id}) {{
                    background-color: {bg_color} !important;
                }}
                </style>
                """, unsafe_allow_html=True)
            
            try:
                # Daten extrahieren
                if len(st.session_state.watchlist) > 1:
                    df = all_data.xs(ticker, axis=1, level=1)
                else:
                    df = all_data
                
                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    eval_txt = "Überkauft" if rsi_v > 70 else ("Überverkauft" if rsi_v < 30 else "Neutral")

                    # STUFE 1: HEADER
                    st.markdown(f"""
                        <div class="header-section">
                            <div class="info-box">{ticker} : {price:.2f}</div>
                            <div class="rsi-box">RSI (14): {rsi_v:.2f} - {eval_txt}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART IN PFIRSICH BOX
                    st.markdown('<div class="chart-container"><div class="chart-peach-box">', unsafe_allow_html=True)
                    fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                    fig.add_hline(y=70, line_dash="dash", line_color="red")
                    fig.add_hline(y=30, line_dash="dash", line_color="green")
                    fig.update_layout(
                        height=220, margin=dict(l=10,r=10,t=10,b=10),
                        paper_bgcolor='#f7cbb4', plot_bgcolor='#f7cbb4',
                        font=dict(color="#1a3d5e", size=11),
                        xaxis=dict(showgrid=False), yaxis=dict(range=[0,100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div></div>', unsafe_allow_html=True)

                    # STUFE 3: BUTTON
                    st.markdown('<div class="button-container">', unsafe_allow_html=True)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_"+ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            except: continue
