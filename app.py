import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION & DATENBANK ---
DB_NAME = "watchlist_ultimate_final.db"
# Eine Auswahl an kräftigen Hintergrundfarben für die Aktien-Module
MODULE_COLORS = ["#2b306b", "#145c48", "#5c143a", "#3d145c", "#144c5c"]


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
        try:
            sl = st.secrets.get("START_STOCKS", "")
            if sl:
                data = [s.strip() for s in sl.split(",") if s.strip()]
                for s in data: add_to_db(s)
        except:
            data = ["AAPL"]
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


def trigger_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# --- DATEN LOGIK ---
@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


@st.cache_data(ttl=3600)
def get_isin_num(symbol):
    try:
        t = yf.Ticker(symbol)
        return t.isin if t.isin else "-"
    except:
        return "-"


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker Ultimate", layout="wide")
init_db()

# CSS FÜR DAS UMSCHLIESSENDE MODUL UND DAS LAYOUT
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }

    /* Laptop-Zentrierung */
    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* WICHTIG: Erzwingt die Hintergrundfarbe für den GANZEN Block (Header, Chart, Button) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.color-marker) {
        border-radius: 30px !important;
        border: none !important;
        padding: 0px !important;
        margin-bottom: 35px !important;
        overflow: hidden !important;
    }

    /* Modul-Header (Stufe 1) */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 25px 25px 10px 25px;
        width: 100%;
    }
    .header-left { display: flex; align-items: baseline; gap: 12px; }
    .stock-name { font-size: 2.2em; font-weight: bold; }
    .stock-isin { font-size: 1em; color: rgba(255,255,255,0.6); }
    .stock-price { font-size: 1.8em; margin-left: 15px; font-weight: bold; color: #fff; }

    /* RSI-Bewertung rechts oben */
    .rsi-eval-box {
        font-size: 1.4em;
        font-weight: bold;
        padding: 12px 20px;
        border-radius: 15px;
        border: 2px solid white;
    }
    .buy { color: #00ff88; border-color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { color: #ff4e4e; border-color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { color: #ffcc00; border-color: #ffcc00; background: rgba(255,204,0,0.1); }

    /* Button Design (Stufe 3) */
    div.stButton > button {
        background-color: #34495e !important; /* Dunkelblau-Grau für Kontrast */
        color: white !important;
        border: none !important;
        border-radius: 0px !important; /* Schließt bündig ab */
        height: 55px !important;
        width: 100% !important;
        font-weight: bold !important;
        font-size: 1.1em !important;
        margin-top: -5px !important;
    }
    div.stButton > button:hover { background-color: #2c3e50 !important; }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# --- SIDEBAR BACKUP ---
with st.sidebar:
    st.header("⚙️ Verwaltung")
    st.text_area("Watchlist Backup:", value=",".join(st.session_state.watchlist), height=80)

st.title("📈 RSI Tracker")

# SUCHE
search = st.text_input("Aktie / ISIN / WKN suchen:", placeholder="z.B. Tesla, Apple...")
if len(search) > 1:
    res = yf.Search(search, max_results=5).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res}
        sel = st.selectbox("Ergebnis wählen:", options.keys())
        if st.button("➕ Hinzufügen", use_container_width=True):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                add_to_db(sym)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# --- ANZEIGE DER MODULE ---
if st.session_state.watchlist:
    all_data = fetch_data(st.session_state.watchlist)

    for i, ticker in enumerate(st.session_state.watchlist):
        bg_color = MODULE_COLORS[i % len(MODULE_COLORS)]
        # ID-Bereinigung für CSS
        safe_id = ticker.replace(".", "").replace("-", "")

        # UMSCHLIESSENDER CONTAINER
        with st.container(border=True):
            # Marker und spezifisches CSS für diesen Ticker
            st.markdown(f"""
                <div class="color-marker" id="block-{safe_id}"></div>
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#block-{safe_id}) {{
                    background-color: {bg_color} !important;
                }}
                </style>
                """, unsafe_allow_html=True)

            try:
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    isin = get_isin_num(ticker)
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]

                    # Status Logik
                    cl = "buy" if rsi_v < 30 else "sell" if rsi_v > 70 else "neutral"
                    stat = "Kaufzone" if cl == "buy" else ("Verkaufzone" if cl == "sell" else "Neutral")

                    # STUFE 1: HEADER
                    st.markdown(f"""
                        <div class="module-header">
                            <div class="header-left">
                                <span class="stock-name">{ticker} : <span class="stock-isin">{isin}</span></span>
                                <span class="stock-price">{price:.2f}</span>
                            </div>
                            <div class="rsi-eval-box {cl}">RSI (14): {rsi_v:.2f} - {stat}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART (Mittelteil)
                    # Wir machen den Chart transparent, damit die Modul-Farbe durchgeht
                    fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                    fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                    fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                    fig.update_layout(
                        height=180, margin=dict(l=20, r=20, t=0, b=10),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="white"), xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # STUFE 3: BUTTON
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.cache_data.clear()
                        trigger_rerun()
            except:
                st.error(f"Fehler bei {ticker}")