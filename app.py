import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json
import os


# --- KOMPATIBILITÄTS-FUNKTION (Neustart) ---
def trigger_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# --- SICHERHEIT (Über Streamlit Secrets) ---
def check_password():
    """Gibt True zurück, wenn das Passwort korrekt ist."""
    if "password_correct" not in st.session_state:
        st.title("🔒 Sicherer Zugriff")
        st.write("Bitte gib dein Passwort ein, um den RSI Tracker zu nutzen.")

        # Das Passwort wird sicher aus den Streamlit Secrets geladen
        # Du musst es in der Streamlit Cloud unter Settings -> Secrets hinterlegen!
        try:
            richtiges_passwort = st.secrets["MY_PASSWORD"]
        except:
            st.error("Fehler: Kein Passwort in den Streamlit-Secrets gefunden!")
            st.stop()

        user_input = st.text_input("Passwort", type="password")
        if st.button("Anmelden", use_container_width=True):
            if user_input == richtiges_passwort:
                st.session_state.password_correct = True
                trigger_rerun()
            else:
                st.error("Falsches Passwort!")
        return False
    return True


# Passwort-Abfrage starten
if not check_password():
    st.stop()


# --- DATEN-FUNKTIONEN (Optimiert mit Caching) ---
@st.cache_data(ttl=300)
def get_stock_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


@st.cache_data(ttl=3600)
def search_ticker(query):
    try:
        search = yf.Search(query, max_results=5)
        return search.quotes
    except:
        return []


DB_FILE = "aktien_liste.json"


def load_watchlist():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return ["AAPL", "TSLA"]
    return ["AAPL", "TSLA"]


def save_watchlist(watchlist):
    with open(DB_FILE, "w") as f: json.dump(watchlist, f)


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# --- DESIGN & LAYOUT ---
st.set_page_config(page_title="RSI Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c3d; color: white; }

    /* Button Design: Blau mit weißem Text */
    div.stButton > button {
        background-color: #4e8cff !important;
        color: white !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        height: 50px !important;
        border: none !important;
    }

    /* Eingabefelder: Schwarzer Text beim Tippen */
    input { color: #000 !important; font-weight: bold !important; }

    /* Karten-Design für die Aktien */
    .card {
        background: linear-gradient(135deg, #2b306b 0%, #1e224f 100%);
        padding: 20px;
        border-radius: 15px;
        border-left: 8px solid #4e8cff;
        margin-bottom: 5px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    .buy { color: #00ff88; font-weight: bold; }
    .sell { color: #ff4e4e; font-weight: bold; }
    .neutral { color: #ffcc00; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 Mein RSI Tracker")

# --- SUCHE ---
st.subheader("Aktie suchen (Name, WKN oder Symbol)")
search_input = st.text_input("Suche...", placeholder="z.B. Apple, Volkswagen...", label_visibility="collapsed")

if len(search_input) > 1:
    results = search_ticker(search_input)
    if results:
        options = {f"{r.get('shortname', 'Info')} ({r.get('symbol')})": r.get('symbol') for r in results if
                   r.get('shortname')}
        selection = st.selectbox("Ergebnis auswählen:", options.keys())
        if st.button("➕ Zur Liste hinzufügen", use_container_width=True):
            sym = options[selection]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                save_watchlist(st.session_state.watchlist)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# --- ANZEIGE DER TRACKER ---
if st.session_state.watchlist:
    all_data = get_stock_data(st.session_state.watchlist)

    for ticker in st.session_state.watchlist:
        try:
            # Daten-Extraktion
            if len(st.session_state.watchlist) > 1:
                df = all_data.xs(ticker, axis=1, level=1)
            else:
                df = all_data

            if not df.empty:
                rsi_series = calc_rsi(df['Close'])
                curr_rsi = float(rsi_series.iloc[-1])
                curr_price = float(df['Close'].iloc[-1])

                # Bewertung (RSI 14 Tage Interval)
                l_class = "buy" if curr_rsi < 30 else "sell" if curr_rsi > 70 else "neutral"
                rating = "KAUFEN (Überverkauft)" if curr_rsi < 30 else "VERKAUFEN (Überkauft)" if curr_rsi > 70 else "Neutral"

                st.markdown(f"""
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.4em; font-weight:bold;">{ticker}</span>
                        <span class="{l_class}" style="font-size:1.1em;">{rating}</span>
                    </div>
                    <div style="margin-top:10px;">
                        Preis: <b>{curr_price:.2f}</b> | RSI (14): <b class="{l_class}">{curr_rsi:.2f}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Plotly Chart
                fig = go.Figure(go.Scatter(x=df.index, y=rsi_series, line=dict(color='#4e8cff', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=160, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)',
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))

                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                    st.session_state.watchlist.remove(ticker)
                    save_watchlist(st.session_state.watchlist)
                    st.cache_data.clear()
                    trigger_rerun()
        except:
            continue

if st.sidebar.button("Abmelden", use_container_width=True):
    st.session_state.clear()
    trigger_rerun()