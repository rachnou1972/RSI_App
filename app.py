import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json
import os


# --- KOMPATIBILITÄTS-FUNKTION (Gegen Rerun-Fehler) ---
def trigger_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# --- SICHERHEIT (Gegen Fremdzugriff) ---
MEIN_PASSWORT = "trader2025"


def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Sicherer Zugriff")
        user_input = st.text_input("Bitte Passwort eingeben:", type="password")
        if st.button("Anmelden", use_container_width=True):
            if user_input == MEIN_PASSWORT:
                st.session_state.password_correct = True
                trigger_rerun()
            else:
                st.error("Falsches Passwort!")
        return False
    return True


if not check_password():
    st.stop()


# --- DATEN-LOGIK ---
@st.cache_data(ttl=300)
def get_stock_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


@st.cache_data(ttl=3600)
def search_ticker(query):
    try:
        search = yf.Search(query, max_results=5)
        return search.quotes  # Nutzt .quotes für Kompatibilität
    except:
        return []


DB_FILE = "aktien_liste.json"


def load_watchlist():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return ["AAPL"]
    return ["AAPL"]


def save_watchlist(watchlist):
    with open(DB_FILE, "w") as f: json.dump(watchlist, f)


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# --- DESIGN SETUP ---
st.set_page_config(page_title="RSI Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c3d; color: white; }
    div.stButton > button {
        background-color: #4e8cff !important; color: white !important;
        border-radius: 10px; font-weight: bold; height: 45px;
    }
    input { color: #000 !important; font-weight: bold !important; }
    .card {
        background-color: #2b306b; padding: 15px; border-radius: 12px;
        border-left: 6px solid #4e8cff; margin-bottom: 5px;
    }
    .buy { color: #00ff88; font-weight: bold; }
    .sell { color: #ff4e4e; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 Mein RSI Tracker")

# --- SUCHE (Vorschläge beim Tippen) ---
search_query = st.text_input("Aktie suchen:", placeholder="Name, WKN oder Symbol...")
if search_query:
    results = search_ticker(search_query)
    if results:
        options = {f"{r.get('shortname', 'Info')} ({r.get('symbol')})": r.get('symbol') for r in results if
                   r.get('shortname')}
        selection = st.selectbox("Ergebnis wählen:", options.keys())
        if st.button("➕ Hinzufügen", use_container_width=True):
            sym = options[selection]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                save_watchlist(st.session_state.watchlist)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# --- ANZEIGE DER CARDS ---
if st.session_state.watchlist:
    all_data = get_stock_data(st.session_state.watchlist)

    for ticker in st.session_state.watchlist:
        try:
            # Ticker-Daten extrahieren
            if len(st.session_state.watchlist) > 1:
                df = all_data.xs(ticker, axis=1, level=1)
            else:
                df = all_data

            if not df.empty:
                rsi_series = calc_rsi(df['Close'])
                curr_rsi = float(rsi_series.iloc[-1])
                curr_price = float(df['Close'].iloc[-1])

                l_class = "buy" if curr_rsi < 30 else "sell" if curr_rsi > 70 else ""
                rating = "ÜBERVERKAUFT" if curr_rsi < 30 else "ÜBERKAUFT" if curr_rsi > 70 else "Neutral"

                st.markdown(f"""
                <div class="card">
                    <div style="display:flex; justify-content:space-between;">
                        <b>{ticker}</b> <span class="{l_class}">{rating}</span>
                    </div>
                    <div>Preis: {curr_price:.2f} | RSI (14): <b class="{l_class}">{curr_rsi:.2f}</b></div>
                </div>
                """, unsafe_allow_html=True)

                # Plotly Chart
                fig = go.Figure(go.Scatter(x=df.index, y=rsi_series, line=dict(color='#4e8cff', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                fig.add_hline(y=30, line_dash="dash", line_color="green")
                fig.update_layout(height=160, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)',
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), yaxis=dict(range=[0, 100]))

                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                if st.button(f"🗑️ {ticker} löschen", key="del_" + ticker, use_container_width=True):
                    st.session_state.watchlist.remove(ticker)
                    save_watchlist(st.session_state.watchlist)
                    st.cache_data.clear()
                    trigger_rerun()
        except:
            continue

if st.sidebar.button("Abmelden", use_container_width=True):
    st.session_state.clear()
    trigger_rerun()