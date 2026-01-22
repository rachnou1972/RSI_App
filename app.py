import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK & SETUP ---
DB_NAME = "watchlist_final_v20.db"
# Hintergrundfarben für die Module (Blau, Dunkelgrün, Weinrot, Violett, Petrol)
MODULE_COLORS = ["#1e537d", "#145c48", "#7d1e3d", "#4b1e7d", "#1e727d"]


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


def calc_rsi(series, period=14):
    if len(series) < period: return pd.Series([50] * len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker Ultimate", layout="wide")
init_db()

# --- CSS FÜR DAS DESIGN NACH ZEICHNUNG ---
st.markdown("""
    <style>
    /* Hintergrund der App */
    .stApp { background-color: #0e1117; color: white; }

    /* Laptop-Zentrierung */
    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* Das umschließende UI-Element (Der Rahmen um alles) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.stock-marker) {
        border-radius: 40px !important;
        padding: 30px !important;
        margin-bottom: 50px !important;
        border: none !important;
        overflow: hidden !important;
    }

    /* Header Bereich (Stufe 1) */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        margin-bottom: 20px;
    }

    /* Box Oben Links (Symbol & Preis) */
    .info-box {
        background-color: #d1e8ff; /* Hellblau/Grau wie Zeichnung */
        padding: 10px 20px;
        border-radius: 5px;
        color: #ff0000; /* Roter Text für Ticker */
        font-weight: bold;
        font-size: 1.2em;
        display: flex;
        gap: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    /* Box Oben Rechts (RSI Bewertung) */
    .rsi-box-eval {
        background-color: #ffb400; /* Gold/Gelb wie Zeichnung */
        padding: 10px 20px;
        border-radius: 5px;
        color: black;
        font-weight: bold;
        font-size: 1.5em;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    /* Chart Container (Stufe 2) */
    .chart-frame {
        background-color: #f7cbb4; /* Pfirsich/Hautfarbe wie Zeichnung */
        border-radius: 20px;
        padding: 10px;
        border: 2px solid #333;
        margin-bottom: 20px;
    }

    /* Button Container (Stufe 3) */
    div.stButton > button {
        background-color: #c4f3ce !important; /* Hellgrün wie Zeichnung */
        color: #1a3d34 !important;
        border-radius: 15px !important;
        height: 65px !important;
        font-size: 1.8em !important;
        font-weight: bold !important;
        border: 2px solid #333 !important;
        width: 100% !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    /* Smartphone Optimierung */
    @media (max-width: 600px) {
        .header-container { flex-direction: column; gap: 10px; align-items: flex-start; }
        .rsi-box-eval { font-size: 1.1em; width: 100%; text-align: center; }
        .info-box { font-size: 1em; width: 100%; }
        div.stButton > button { font-size: 1.3em !important; height: 50px !important; }
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Aktie suchen (Name/ISIN/WKN):", placeholder="Tippen zum Suchen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Wähle:", options.keys())
            if st.button("➕ Hinzufügen", use_container_width=True):
                sym = options[sel]
                if sym not in st.session_state.watchlist:
                    st.session_state.watchlist.append(sym)
                    add_to_db(sym)
                    st.rerun()
    except:
        pass

st.divider()

# --- ANZEIGE DER MODULE NACH ZEICHNUNG ---
if st.session_state.watchlist:
    # Batch Download
    try:
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.error("Daten konnten nicht geladen werden.")
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        bg_modul = MODULE_COLORS[i % len(MODULE_COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")

        # CONTAINER FÜR DAS MODUL
        with st.container(border=True):
            # Marker für CSS
            st.markdown(f'<div class="stock-marker" id="m-{safe_id}"></div>', unsafe_allow_html=True)
            # Erzwinge die Hintergrundfarbe des Moduls
            st.markdown(
                f"""<style>div[data-testid="stVerticalBlockBorderWrapper"]:has(#m-{safe_id}) {{ background-color: {bg_modul} !important; }}</style>""",
                unsafe_allow_html=True)

            try:
                # Daten Extraktion
                if len(st.session_state.watchlist) > 1:
                    df = all_data.xs(ticker, axis=1, level=1)
                else:
                    df = all_data

                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    eval_text = "Überkauft" if rsi_v > 70 else ("Überverkauft" if rsi_v < 30 else "Neutral")

                    # STUFE 1: HEADER (Zwei Boxen)
                    st.markdown(f"""
                        <div class="header-container">
                            <div class="info-box">{ticker} : {price:.2f}</div>
                            <div class="rsi-box-eval">RSI (14): {rsi_v:.2f} - {eval_text}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART (Mitte)
                    st.markdown('<div class="chart-frame">', unsafe_allow_html=True)
                    fig = go.Figure(
                        go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                    fig.add_hline(y=70, line_dash="dash", line_color="red")
                    fig.add_hline(y=30, line_dash="dash", line_color="green")
                    fig.update_layout(
                        height=220, margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor='#f7cbb4', plot_bgcolor='#f7cbb4',  # Pfirsich Hintergrund
                        font=dict(color="#1a3d5e", size=12),
                        xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div>', unsafe_allow_html=True)

                    # STUFE 3: BUTTON (Unten)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
            except:
                st.error(f"Fehler bei {ticker}")