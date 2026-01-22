import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_pro_v3.db"
# Eine Palette schöner, dunkler Farben für die Module
MODULE_COLORS = ["#2b306b", "#1e4f47", "#4f1e3a", "#3e1e4f", "#1e3b4f", "#2d2d2d"]


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
        try:
            secret_list = st.secrets.get("START_STOCKS", "")
            if secret_list:
                data = [s.strip() for s in secret_list.split(",") if s.strip()]
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
            st.error("Bitte MY_PASSWORD in den Secrets setzen!"); st.stop()
        u_input = st.text_input("Passwort", type="password")
        if st.button("Anmelden", use_container_width=True):
            if u_input == pw:
                st.session_state.password_correct = True
                trigger_rerun()
            else:
                st.error("Falsches Passwort!")
        return False
    return True


# --- DATEN LOGIK ---
@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


@st.cache_data(ttl=3600)
def get_isin(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        return t.isin if t.isin else "N/A"
    except:
        return "N/A"


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Pro Tracker", layout="wide")
init_db()

# Passwort prüfen
if not check_password():
    st.stop()

# CSS für das Drei-Stufen-Modul
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }

    /* Zentrierung für Laptop */
    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* Das umschließende UI-Modul */
    .stock-module {
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 30px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.6);
    }

    /* Stufe 1: Header */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        margin-bottom: 15px;
    }

    .info-group {
        display: flex;
        align-items: baseline;
        gap: 15px;
    }

    .stock-title { font-size: 2.2em; font-weight: bold; }
    .stock-isin { font-size: 1em; color: #bbb; }
    .stock-price { font-size: 1.6em; font-weight: normal; margin-left: 10px; }

    /* Stufe 1: RSI Bubble rechts */
    .rsi-bubble {
        padding: 10px 20px;
        border-radius: 12px;
        font-size: 1.3em;
        font-weight: bold;
        text-align: center;
        border: 2px solid;
    }

    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }

    /* Button Styling */
    div.stButton > button {
        background-color: #ff4e4e !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
    }

    .search-area { background-color: #1a1c3d; padding: 20px; border-radius: 15px; margin-bottom: 20px; }
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Verwaltung")
    current_list = ",".join(st.session_state.watchlist)
    st.text_area("Backup (für Secrets):", value=current_list, height=100)
    if st.button("Abmelden", use_container_width=True):
        st.session_state.clear()
        trigger_rerun()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
with st.container():
    search = st.text_input("Aktie / ISIN / WKN suchen:", placeholder="z.B. Apple, Tesla, US0378331005...")
    if len(search) > 1:
        res = yf.Search(search, max_results=5).quotes
        if res:
            options = {f"{r.get('shortname')} ({r.get('symbol')}) - {r.get('exchDisp')}": r.get('symbol') for r in res}
            sel = st.selectbox("Ergebnis auswählen:", options.keys())
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
    # Alle Daten auf einmal laden (Batch)
    all_data = fetch_data(st.session_state.watchlist)

    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            # Hintergrundfarbe für dieses Modul festlegen
            bg_color = MODULE_COLORS[i % len(MODULE_COLORS)]

            # Daten extrahieren
            df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data

            if not df.empty:
                isin = get_isin(ticker)
                rsi_val = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]

                # Bewertung bestimmen
                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                status = "Kaufzone" if rsi_val < 30 else "Verkaufzone" if rsi_val > 70 else "Neutral"

                # DAS MODUL STARTET
                st.markdown(f"""
                <div class="stock-module" style="background-color: {bg_color};">
                    <!-- STUFE 1: Info & Bubble -->
                    <div class="module-header">
                        <div class="info-group">
                            <span class="stock-title">{ticker} : <span class="stock-isin">{isin}</span></span>
                            <span class="stock-price">Preis: {price:.2f}</span>
                        </div>
                        <div class="rsi-bubble {cl}">
                            RSI (14): {rsi_val:.2f} - {status}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # STUFE 2: Chart (Wird optisch in das Modul geschoben)
                # Wir machen den Chart-Hintergrund transparent, damit die Modul-Farbe durchscheint
                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(
                    height=200, margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="white"),
                    xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                )

                # Das CSS "margin-top: -50px" rückt den Chart visuell in das Modul
                st.markdown('<div style="margin-top: -40px;">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)

                # STUFE 3: Der Button
                if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                    st.session_state.watchlist.remove(ticker)
                    remove_from_db(ticker)
                    st.cache_data.clear()
                    trigger_rerun()

                # Abstand zum nächsten Modul
                st.markdown("<br>", unsafe_allow_html=True)
        except Exception as e:
            continue