import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK & SETUP ---
DB_NAME = "watchlist_v11.db"
# Kräftige Farben (Blau, Grün, Lila, Petrol, Anthrazit)
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#0f766e", "#334155"]


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
    if not data:
        sl = st.secrets.get("START_STOCKS", "AAPL,TSLA")
        data = [s.strip() for s in sl.split(",") if s.strip()]
    return data


def add_to_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('INSERT OR REPLACE INTO watchlist VALUES (?)', (symbol,))
        conn.commit()
    except:
        pass
    conn.close()


def remove_from_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()


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
st.set_page_config(page_title="RSI Ultimate", layout="wide")
init_db()

# CSS UM DEN SCHWARZEN HINTERGRUND ZU ÜBERSCHREIBEN
st.markdown("""
    <style>
    /* Basis-App */
    .stApp { background-color: #0e1117; color: white; }

    /* Laptop Zentrierung */
    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* ERZWINGE DIE FARBE DES GESAMTEN MODULS */
    /* Wir zielen auf den Border-Wrapper von Streamlit ab */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.stock-module-marker) {
        border: none !important;
        border-radius: 30px !important;
        padding: 0px !important;
        margin-bottom: 40px !important;
        overflow: hidden !important;
    }

    /* Header Design */
    .mod-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 25px 25px 10px 25px;
        width: 100%;
    }
    .header-info { display: flex; align-items: baseline; gap: 12px; }
    .ticker-name { font-size: 2.2em; font-weight: bold; }
    .isin-val { font-size: 1em; color: rgba(255,255,255,0.6); }
    .price-val { font-size: 1.8em; margin-left: 15px; font-weight: bold; }

    /* RSI Bubble Rechts */
    .rsi-bubble {
        padding: 12px 22px;
        border-radius: 15px;
        font-size: 1.3em;
        font-weight: bold;
        border: 2px solid white;
    }
    .buy { background: rgba(0,255,136,0.2); color: #00ff88; border-color: #00ff88; }
    .sell { background: rgba(255,78,78,0.2); color: #ff4e4e; border-color: #ff4e4e; }
    .neutral { background: rgba(255,204,0,0.2); color: #ffcc00; border-color: #ffcc00; }

    /* Button ganz unten im Modul */
    div.stButton > button {
        border-radius: 0px !important;
        background-color: #334155 !important; /* Dunkles Grau-Blau */
        color: white !important;
        height: 55px !important;
        width: 100% !important;
        border: none !important;
        font-weight: bold !important;
        margin-top: -5px !important;
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker")

# SUCHE
search = st.text_input("Suchen (Name, ISIN, Ticker):")
if len(search) > 1:
    res = yf.Search(search, max_results=5).quotes
    if res:
        opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
        sel = st.selectbox("Auswählen:", opts.keys())
        if st.button("➕ Hinzufügen", use_container_width=True):
            s = opts[sel]
            if s not in st.session_state.watchlist:
                st.session_state.watchlist.append(s)
                add_to_db(s)
                st.rerun()

st.divider()

# ANZEIGE DER MODULE
if st.session_state.watchlist:
    all_data = fetch_data(st.session_state.watchlist)

    for i, ticker in enumerate(st.session_state.watchlist):
        bg = COLORS[i % len(COLORS)]
        clean_id = ticker.replace(".", "").replace("-", "")

        # CONTAINER MIT BORDER UM ALLES EINZUSCHLIESSEN
        with st.container(border=True):
            # Unsichtbarer Marker für CSS
            st.markdown(f'<div class="stock-module-marker" id="mark-{clean_id}"></div>', unsafe_allow_html=True)

            # SPEZIFISCHES CSS UM GENAU DIESEN BLOCK ZU FÄRBEN
            st.markdown(f"""
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#mark-{clean_id}) {{
                    background-color: {bg} !important;
                }}
                </style>
                """, unsafe_allow_html=True)

            try:
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    # ISIN holen
                    isin = yf.Ticker(ticker).isin if hasattr(yf.Ticker(ticker), 'isin') else "-"
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]

                    cl = "buy" if rsi_v < 30 else "sell" if rsi_v > 70 else "neutral"
                    stat = "Kaufzone" if cl == "buy" else ("Verkaufzone" if cl == "sell" else "Neutral")

                    # STUFE 1: HEADER
                    st.markdown(f"""
                        <div class="mod-header">
                            <div class="header-info">
                                <span class="ticker-name">{ticker} : <span class="isin-val">{isin}</span></span>
                                <span class="price-val">{price:.2f}</span>
                            </div>
                            <div class="rsi-bubble {cl}">RSI (14): {rsi_v:.2f} - {stat}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART (Transparent)
                    fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                    fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                    fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                    fig.update_layout(
                        height=200, margin=dict(l=20, r=20, t=0, b=10),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="white"), xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # STUFE 3: BUTTON
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
            except:
                st.error(f"Fehler bei {ticker}")