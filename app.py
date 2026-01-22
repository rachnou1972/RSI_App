import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3

# --- DATENBANK ---
DB_NAME = "watchlist.db"
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
    return data if data else ["AAPL", "TSLA"]

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
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker", layout="wide")
init_db()

# --- EXAKTES CSS FÜR DAS 3-STUFEN-DESIGN ---
st.markdown("""
    <style>
    /* Mobile-First Design */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Laptop-Zentrierung (850px breit und mittig) */
    @media (min-width: 768px) {
        .main .block-container { 
            max-width: 850px !important; 
            margin: auto !important; 
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
    }
    
    /* WICHTIG: ENTFERNT ALLE RÄNDER UND ABSTÄNDE ZWISCHEN CONTAINERN */
    div[data-testid="stVerticalBlock"] > div[style*="flex"] {
        gap: 0px !important;
    }
    
    /* STUFE 0: ÄUSSERER RAHMEN (OHNE LÜCKEN) */
    .outer-module-frame {
        border-radius: 25px !important;
        overflow: hidden !important;
        margin-bottom: 30px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    
    /* STUFE 1: HEADER BEREICH */
    .header-stage {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 25px !important;
        width: 100%;
    }
    
    /* Linke Box: Hellblau mit Ticker:Preis */
    .ticker-box {
        background-color: #d1e8ff !important;
        padding: 12px 20px !important;
        border-radius: 15px !important;
        color: #000 !important;
        font-weight: bold !important;
        font-size: 1.2em !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.1) !important;
    }
    
    /* Rechte Box: Gelb mit RSI Bewertung */
    .rsi-box {
        background-color: #ffb400 !important;
        padding: 12px 20px !important;
        border-radius: 15px !important;
        color: #000 !important;
        font-weight: bold !important;
        font-size: 1.3em !important;
        border: 2px solid rgba(0,0,0,0.2) !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.1) !important;
        text-align: center !important;
    }
    
    /* STUFE 2: MITTE - CHART CONTAINER (PFIRSICH) */
    .chart-stage {
        background-color: #f7cbb4 !important;
        margin: 0 25px 15px 25px !important;
        border-radius: 20px !important;
        padding: 20px !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    
    /* STUFE 3: UNTEN - BUTTON CONTAINER (HELLGRÜN) */
    .button-stage {
        background-color: #c4f3ce !important;
        margin: 0 25px 25px 25px !important;
        border-radius: 15px !important;
        padding: 0px !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
        overflow: hidden !important;
    }
    
    /* Entfernen-Button */
    .button-stage button {
        background-color: transparent !important;
        color: #1a3d34 !important;
        border: none !important;
        height: 60px !important;
        font-size: 1.5em !important;
        font-weight: bold !important;
        width: 100% !important;
        border-radius: 0px !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .button-stage button:hover {
        background-color: rgba(26, 61, 52, 0.1) !important;
    }
    
    /* Suchfeld */
    div.stTextInput > div > div > input {
        color: #000 !important;
        font-weight: bold !important;
        background-color: white !important;
        border-radius: 10px !important;
        padding: 12px !important;
        border: 2px solid #ddd !important;
    }
    
    /* Mobile Optimierung */
    @media (max-width: 600px) {
        .header-stage {
            flex-direction: column;
            gap: 15px;
            padding: 20px !important;
        }
        
        .ticker-box, .rsi-box {
            width: 100% !important;
            text-align: center;
        }
        
        .chart-stage {
            margin: 0 15px 10px 15px !important;
            padding: 15px !important;
        }
        
        .button-stage {
            margin: 0 15px 20px 15px !important;
        }
        
        .button-stage button {
            height: 50px !important;
            font-size: 1.3em !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Session State initialisieren
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE MIT YFINANCE ---
search = st.text_input("Aktie suchen (Name/Symbol/WKN):", placeholder="z.B. Apple, AAPL, US0378331005...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            # Erstelle Auswahloptionen
            options = {}
            for r in res:
                if r.get('shortname') and r.get('symbol'):
                    name = r.get('shortname', 'Unbekannt')
                    symbol = r.get('symbol')
                    # Zeige auch WKN/ISIN falls verfügbar
                    exchange = r.get('exchange', '')
                    options[f"{name} ({symbol}) - {exchange}"] = symbol
            
            if options:
                selected = st.selectbox("Wähle eine Aktie:", list(options.keys()))
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("➕ Hinzufügen", use_container_width=True):
                        symbol_to_add = options[selected]
                        if symbol_to_add not in st.session_state.watchlist:
                            st.session_state.watchlist.append(symbol_to_add)
                            add_to_db(symbol_to_add)
                            st.rerun()
    except Exception as e:
        st.warning("Suche konnte nicht durchgeführt werden. Bitte versuche es mit einem anderen Suchbegriff.")

st.divider()

# --- ANZEIGE DER AKTIEN-MODULE ---
if st.session_state.watchlist:
    try:
        # Batch-Download aller Aktien
        all_data = yf.download(
            st.session_state.watchlist, 
            period="3mo", 
            interval="1d", 
            progress=False,
            group_by='ticker'
        )
    except:
        st.error("Fehler beim Laden der Aktiendaten")
        all_data = None
    
    if all_data is not None and not all_data.empty:
        for i, ticker in enumerate(st.session_state.watchlist):
            color = COLORS[i % len(COLORS)]
            
            # Erstelle CSS für jedes Modul mit eigener Farbe
            st.markdown(f"""
                <style>
                .outer-module-frame-{i} {{
                    background-color: {color} !important;
                }}
                </style>
            """, unsafe_allow_html=True)
            
            # ÄUßERER RAHMEN (STUFE 0)
            with st.container():
                st.markdown(f'<div class="outer-module-frame outer-module-frame-{i}">', unsafe_allow_html=True)
                
                try:
                    # Daten für diese Aktie extrahieren
                    if len(st.session_state.watchlist) > 1:
                        df = all_data[ticker].copy()
                    else:
                        df = all_data.copy()
                    
                    if not df.empty and len(df) > 14:
                        # Berechne RSI
                        rsi_series = calc_rsi(df['Close'])
                        rsi_value = rsi_series.iloc[-1]
                        current_price = df['Close'].iloc[-1]
                        
                        # RSI Bewertung
                        if rsi_value > 70:
                            rsi_eval = "Überkauft"
                        elif rsi_value < 30:
                            rsi_eval = "Überverkauft"
                        else:
                            rsi_eval = "Neutral"
                        
                        # STUFE 1: HEADER MIT ZWEI BOXEN
                        st.markdown(f"""
                            <div class="header-stage">
                                <div class="ticker-box">
                                    {ticker} : ${current_price:.2f}
                                </div>
                                <div class="rsi-box">
                                    RSI: {rsi_value:.1f}<br>
                                    <small>{rsi_eval}</small>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # STUFE 2: CHART CONTAINER (PFIRSICH)
                        st.markdown('<div class="chart-stage">', unsafe_allow_html=True)
                        
                        # Erstelle RSI Chart
                        fig = go.Figure()
                        
                        # RSI Linie
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=rsi_series,
                            mode='lines',
                            line=dict(color='#1a3d5e', width=3),
                            name='RSI (14)'
                        ))
                        
                        # Überkauft/Überverkauft Linien
                        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.7)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.7)
                        
                        # Neutral Bereich schattieren
                        fig.add_hrect(y0=30, y1=70, line_width=0, fillcolor="rgba(0,0,0,0.05)")
                        
                        # Layout optimieren
                        fig.update_layout(
                            height=250,
                            margin=dict(l=0, r=0, t=20, b=0),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#333", size=11),
                            xaxis=dict(
                                showgrid=False,
                                showticklabels=True,
                                tickformat="%b %d"
                            ),
                            yaxis=dict(
                                range=[0, 100],
                                showgrid=False,
                                title_text="RSI",
                                tickvals=[0, 30, 50, 70, 100]
                            ),
                            showlegend=False,
                            hovermode="x unified"
                        )
                        
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # STUFE 3: BUTTON CONTAINER (HELLGRÜN)
                        st.markdown('<div class="button-stage">', unsafe_allow_html=True)
                        
                        if st.button(f"🗑️ {ticker} entfernen", key=f"remove_{ticker}", use_container_width=True):
                            st.session_state.watchlist.remove(ticker)
                            remove_from_db(ticker)
                            st.rerun()
                            
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    else:
                        st.error(f"Nicht genügend Daten für {ticker}")
                        
                except Exception as e:
                    st.error(f"Fehler bei {ticker}: {str(e)}")
                    # Trotzdem Entfernen-Button anzeigen
                    st.markdown('<div class="button-stage">', unsafe_allow_html=True)
                    if st.button(f"🗑️ {ticker} entfernen", key=f"remove_err_{ticker}", use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.warning("Keine Aktiendaten verfügbar. Bitte überprüfe deine Internetverbindung.")
        
else:
    st.info("Deine Watchlist ist leer. Suche oben nach Aktien und füge sie hinzu!")

# Info Footer
st.markdown("---")
st.caption("📊 **RSI Tracker Pro** • Relative Strength Index (14 Tage) • Daten von Yahoo Finance")
