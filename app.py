import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_ultimate_v15.db"
# Kräftige Modul-Farben (Blau, Grün, Lila, Petrol, Anthrazit)
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#0f766e", "#334155"]


# --- DATENBANK ---
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
        return ["AAPL", "TSLA"]
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


# --- RSI BERECHNUNG ---
def calc_rsi(series, period=14):
    if len(series) < period: return pd.Series([50] * len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker Pro", layout="wide")
init_db()

# CSS FÜR DIE UMSCHLIESSUNG UND MOBILE OPTIMIERUNG
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }

    /* Laptop-Zentrierung */
    @media (min-width: 768px) {
        .main .block-container { max-width: 850px; margin: auto; }
    }

    /* ERZWINGE DIE FARBE DES GESAMTEN MODULS */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.module-marker) {
        border: none !important;
        border-radius: 25px !important;
        padding: 0px !important;
        margin-bottom: 35px !important;
        overflow: hidden !important;
    }

    /* Header Bereich */
    .mod-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        width: 100%;
    }
    .header-left { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
    .ticker-name { font-size: 2.2em; font-weight: bold; color: white; line-height: 1; }
    .price-val { font-size: 1.6em; font-weight: bold; color: white; opacity: 0.9; }

    /* RSI Bubble */
    .rsi-bubble {
        padding: 8px 15px;
        border-radius: 12px;
        font-size: 1.1em;
        font-weight: bold;
        border: 2px solid white;
        text-align: center;
        min-width: 140px;
    }
    .buy { background: rgba(0,255,136,0.2); color: #00ff88; border-color: #00ff88; }
    .sell { background: rgba(255,78,78,0.2); color: #ff4e4e; border-color: #ff4e4e; }
    .neutral { background: rgba(255,204,0,0.2); color: #ffcc00; border-color: #ffcc00; }

    /* Chart Bereich Styling */
    .chart-box { padding: 0 10px; }

    /* Button Styling (Bündig unten) */
    div.stButton > button {
        border-radius: 0px !important;
        background-color: #334155 !important;
        color: white !important;
        height: 50px !important;
        width: 100% !important;
        border: none !important;
        font-weight: bold !important;
        margin-top: -5px !important;
    }

    /* MOBILE OPTIMIERUNG */
    @media (max-width: 600px) {
        .ticker-name { font-size: 1.6em; }
        .price-val { font-size: 1.2em; }
        .rsi-bubble { font-size: 0.9em; padding: 6px 10px; min-width: 110px; }
        .mod-header { padding: 15px; }
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker")

# SUCHE
search = st.text_input("Aktie / ISIN / WKN suchen:", placeholder="Tippen zum Suchen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Ergebnis wählen:", options.keys())
            if st.button("➕ Hinzufügen", use_container_width=True):
                sym = options[sel]
                if sym not in st.session_state.watchlist:
                    st.session_state.watchlist.append(sym)
                    add_to_db(sym)
                    st.rerun()
    except:
        st.error("Suche momentan nicht möglich.")

st.divider()

# MODULE ANZEIGEN
if st.session_state.watchlist:
    # Batch Download (schneller)
    try:
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.error("Fehler beim Laden der Marktdaten.")
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        bg = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")

        # DER UMSCHLIESSENDE CONTAINER (Module)
        with st.container(border=True):
            # Marker für CSS
            st.markdown(f'<div class="module-marker" id="m-{safe_id}"></div>', unsafe_allow_html=True)

            # SPEZIFISCHES CSS UM GENAU DIESEN BLOCK ZU FÄRBEN
            st.markdown(f"""
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#m-{safe_id}) {{
                    background-color: {bg} !important;
                }}
                </style>
                """, unsafe_allow_html=True)

            try:
                # Daten Extraktion (Check ob Multiindex oder nicht)
                if len(st.session_state.watchlist) > 1:
                    df = all_data.xs(ticker, axis=1, level=1)
                else:
                    df = all_data

                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    cl = "buy" if rsi_v < 30 else "sell" if rsi_v > 70 else "neutral"
                    stat = "Kaufzone" if cl == "buy" else ("Verkaufzone" if cl == "sell" else "Neutral")

                    # STUFE 1: HEADER (Name, Preis, Bubble)
                    st.markdown(f"""
                        <div class="mod-header">
                            <div class="header-left">
                                <span class="ticker-name">{ticker}</span>
                                <span class="price-val">{price:.2f}</span>
                            </div>
                            <div class="rsi-bubble {cl}">RSI: {rsi_v:.2f}<br>{stat}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART (Andere Farbe als Modul-Hintergrund für Kontrast)
                    fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                    fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                    fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                    fig.update_layout(
                        height=180, margin=dict(l=10, r=10, t=0, b=5),
                        paper_bgcolor='#1a1a1a', plot_bgcolor='#1a1a1a',  # Dunkler Chart-Kontrast
                        font=dict(color="white"), xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # STUFE 3: BUTTON
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
                else:
                    st.warning(f"Keine Daten für {ticker}")
            except Exception as e:
                st.error(f"Fehler bei {ticker}")