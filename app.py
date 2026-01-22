import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_final_v8.db"
# Kräftige Farben für die Module (Blau, Grün, Violett, Anthrazit, Petrol)
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#312e81", "#134e4a"]


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


# --- SICHERHEIT ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Trader Login")
        try:
            pw = st.secrets["MY_PASSWORD"]
        except:
            st.error("Passwort in Secrets setzen!"); st.stop()
        u_input = st.text_input("Passwort", type="password")
        if st.button("Anmelden", use_container_width=True):
            if u_input == pw:
                st.session_state.password_correct = True
                trigger_rerun()
            else:
                st.error("Falsch!")
        return False
    return True


# --- DATEN LOGIK ---
@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


@st.cache_data(ttl=3600)
def get_isin(symbol):
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

if not check_password():
    st.stop()

# GLOBALER CSS FIX FÜR DAS MODUL-DESIGN
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }

    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* WICHTIG: Erzwingt, dass der umschließende Container keine Standardfarben nutzt */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 20px !important;
        margin-bottom: 35px !important;
        border: none !important;
        padding: 0px !important;
        overflow: hidden !important;
    }

    /* Header Styling */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 25px 20px 10px 20px;
        width: 100%;
    }
    .header-left { display: flex; align-items: baseline; gap: 12px; }
    .s-name { font-size: 2.2em; font-weight: bold; }
    .s-isin { font-size: 1em; color: rgba(255,255,255,0.6); }
    .s-price { font-size: 1.8em; margin-left: 15px; font-weight: bold; }

    /* RSI Bubble */
    .rsi-bubble {
        padding: 12px 22px;
        border-radius: 15px;
        font-size: 1.4em;
        font-weight: bold;
        border: 3px solid white;
    }
    .buy { background: rgba(0,255,136,0.15); color: #00ff88; border-color: #00ff88; }
    .sell { background: rgba(255,78,78,0.15); color: #ff4e4e; border-color: #ff4e4e; }
    .neutral { background: rgba(255,204,0,0.15); color: #ffcc00; border-color: #ffcc00; }

    /* Button Styling am Ende des Moduls */
    div.stButton > button {
        background-color: #ff4e4e !important;
        color: white !important;
        border: none !important;
        border-radius: 0px !important;
        height: 55px !important;
        width: 100% !important;
        font-weight: bold !important;
        margin-top: -5px !important;
    }

    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

with st.sidebar:
    st.header("⚙️ Menü")
    st.text_area("Backup Liste:", value=",".join(st.session_state.watchlist), height=80)
    if st.button("Abmelden", use_container_width=True):
        st.session_state.clear()
        trigger_rerun()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Aktie / ISIN / WKN suchen:")
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

# --- MODULE ANZEIGEN ---
if st.session_state.watchlist:
    all_data = fetch_data(st.session_state.watchlist)

    for i, ticker in enumerate(st.session_state.watchlist):
        color_code = COLORS[i % len(COLORS)]
        # Säuberung des Tickers für CSS-IDs
        safe_id = ticker.replace(".", "").replace("-", "")

        # Erstelle einen umschließenden Container mit Border
        with st.container(border=True):
            # Injektion eines Markers und spezifischen CSS für diesen Ticker
            st.markdown(f"""
                <div id="marker-{safe_id}"></div>
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#marker-{safe_id}) {{
                    background-color: {color_code} !important;
                }}
                </style>
                """, unsafe_allow_html=True)

            try:
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    isin = get_isin(ticker)
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    cl = "buy" if rsi_v < 30 else "sell" if rsi_v > 70 else "neutral"
                    stat = "Kaufzone" if cl == "buy" else ("Verkaufzone" if cl == "sell" else "Neutral")

                    # STUFE 1: HEADER (Name, ISIN, Preis, RSI Box)
                    st.markdown(f"""
                        <div class="module-header">
                            <div class="header-left">
                                <span class="s-name">{ticker} : <span class="s-isin">{isin}</span></span>
                                <span class="s-price">{price:.2f}</span>
                            </div>
                            <div class="rsi-bubble {cl}">RSI (14): {rsi_v:.2f} - {stat}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART (Mittelteil)
                    fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                    fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                    fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                    fig.update_layout(
                        height=180, margin=dict(l=15, r=15, t=0, b=10),
                        paper_bgcolor='#1a1a1a', plot_bgcolor='#1a1a1a',  # Chart Box
                        font=dict(color="white"), xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # STUFE 3: BUTTON (Abschluss unten)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.cache_data.clear()
                        trigger_rerun()
            except:
                st.error(f"Datenfehler bei {ticker}")