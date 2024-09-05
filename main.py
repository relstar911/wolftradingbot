import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from telegram import Bot
import asyncio
import time
import logging
import sys
from config import (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, TELEGRAM_TOKEN, CHAT_ID,
                    CHECK_INTERVAL, SHORT_SMA_PERIOD, LONG_SMA_PERIOD, TP_PIPS, SL_PIPS,
                    MACD_FAST, MACD_SLOW, MACD_SIGNAL, RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
                    ATR_PERIOD, ATR_MULTIPLIER_TP, ATR_MULTIPLIER_SL, MIN_SMA_EMA_DIFF)
import random

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_mt5():
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        error_code, error_message = mt5.last_error()
        logger.error(f"MetaTrader5 Initialisierung fehlgeschlagen. Fehlercode: {error_code}, Nachricht: {error_message}")
        sys.exit(1)
    logger.info("MetaTrader5 erfolgreich initialisiert")

def get_xauusd_price():
    symbol = "XAUUSD"
    timeframe = mt5.TIMEFRAME_M1  # 1-Minuten-Timeframe
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
    
    if rates is None or len(rates) == 0:
        logger.error("Fehler beim Abrufen der XAUUSD-Preisdaten")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df['close'].values

def generate_signal(close):
    if close is None or len(close) < LONG_SMA_PERIOD:
        return None
    
    df = pd.DataFrame({'close': close})
    df['sma_short'] = df['close'].rolling(window=SHORT_SMA_PERIOD).mean()
    df['sma_long'] = df['close'].rolling(window=LONG_SMA_PERIOD).mean()
    df['ema_short'] = df['close'].ewm(span=SHORT_SMA_PERIOD, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=LONG_SMA_PERIOD, adjust=False).mean()
    
    # Calculate RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Calculate MACD
    df['ema_fast'] = df['close'].ewm(span=MACD_FAST, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=MACD_SLOW, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal_line'] = df['macd'].ewm(span=MACD_SIGNAL, adjust=False).mean()
    
    last_price = close[-1]
    sma_diff = df['sma_short'].iloc[-1] - df['sma_long'].iloc[-1]
    ema_diff = df['ema_short'].iloc[-1] - df['ema_long'].iloc[-1]
    rsi = df['rsi'].iloc[-1]
    macd = df['macd'].iloc[-1]
    signal_line = df['signal_line'].iloc[-1]
    
    # Define signal conditions
    sma_crossover = df['sma_short'].iloc[-2] <= df['sma_long'].iloc[-2] and df['sma_short'].iloc[-1] > df['sma_long'].iloc[-1]
    ema_crossover = df['ema_short'].iloc[-2] <= df['ema_long'].iloc[-2] and df['ema_short'].iloc[-1] > df['ema_long'].iloc[-1]
    rsi_oversold = rsi < RSI_OVERSOLD
    rsi_overbought = rsi > RSI_OVERBOUGHT
    macd_crossover = df['macd'].iloc[-2] <= df['signal_line'].iloc[-2] and df['macd'].iloc[-1] > df['signal_line'].iloc[-1]
    
    # Log conditions
    logger.debug(f"SMA Crossover: {sma_crossover}, EMA Crossover: {ema_crossover}")
    logger.debug(f"RSI: {rsi:.2f}, MACD Crossover: {macd_crossover}")
    logger.debug(f"SMA Diff: {sma_diff:.2f}, EMA Diff: {ema_diff:.2f}")
    
    # Generate buy signal
    if (sma_crossover or ema_crossover) and rsi_oversold and macd_crossover and abs(sma_diff) > MIN_SMA_EMA_DIFF and abs(ema_diff) > MIN_SMA_EMA_DIFF:
        tp_pips, sl_pips = calculate_dynamic_tp_sl(close)
        return f"""🔔 Signaltyp: BUY
💰 Einstiegspreis: {last_price:.2f}
🎯 Take-Profit (TP): {last_price+tp_pips/10:.2f}
🛑 Stop-Loss (SL): {last_price-sl_pips/10:.2f}
📊 Zeitrahmen: Kurzfristig
💡 Begründung:
- SMA/EMA Kreuzung nach oben
- RSI überkauft ({rsi:.2f})
- MACD Kreuzung nach oben
- SMA Differenz: {sma_diff:.2f}
- EMA Differenz: {ema_diff:.2f}"""
    
    # Generate sell signal
    elif (sma_crossover or ema_crossover) and rsi_overbought and macd_crossover and abs(sma_diff) > MIN_SMA_EMA_DIFF and abs(ema_diff) > MIN_SMA_EMA_DIFF:
        tp_pips, sl_pips = calculate_dynamic_tp_sl(close)
        return f"""🔔 Signaltyp: SELL
💰 Einstiegspreis: {last_price:.2f}
🎯 Take-Profit (TP): {last_price-tp_pips/10:.2f}
🛑 Stop-Loss (SL): {last_price+sl_pips/10:.2f}
📊 Zeitrahmen: Kurzfristig
💡 Begründung:
- SMA/EMA Kreuzung nach unten
- RSI überverkauft ({rsi:.2f})
- MACD Kreuzung nach unten
- SMA Differenz: {sma_diff:.2f}
- EMA Differenz: {ema_diff:.2f}"""
    
    else:
        logger.debug("No signal generated due to conditions not met.")
        return None

def calculate_dynamic_tp_sl(close, atr_period=ATR_PERIOD):
    df = pd.DataFrame({'close': close})
    df['high'] = df['close']  # Assuming we only have close prices
    df['low'] = df['close']
    
    # Calculate ATR
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift())
    df['tr3'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=atr_period).mean()
    
    current_atr = df['atr'].iloc[-1]
    
    # Dynamic TP and SL based on ATR
    tp_pips = max(TP_PIPS, int(current_atr * ATR_MULTIPLIER_TP * 10))  # 2x ATR, converted to pips
    sl_pips = max(SL_PIPS, int(current_atr * ATR_MULTIPLIER_SL * 10))  # 1x ATR, converted to pips
    
    return tp_pips, sl_pips

def generate_test_signal():
    last_price = random.uniform(2500, 2550)  # Zufälliger Preis zwischen 2500 und 2550
    signal_type = random.choice(["BUY", "SELL"])
    
    if signal_type == "BUY":
        return f"""🔔 Signaltyp: BUY
💰 Einstiegspreis: {last_price:.2f}
🎯 Take-Profit (TP): {last_price+TP_PIPS/10:.2f}
🛑 Stop-Loss (SL): {last_price-SL_PIPS/10:.2f}
📊 Zeitrahmen: Kurzfristig
💡 Begründung: Dies ist ein Testsignal für Demonstrationszwecke."""
    else:
        return f"""🔔 Signaltyp: SELL
💰 Einstiegspreis: {last_price:.2f}
🎯 Take-Profit (TP): {last_price-TP_PIPS/10:.2f}
🛑 Stop-Loss (SL): {last_price+SL_PIPS/10:.2f}
📊 Zeitrahmen: Kurzfristig
💡 Begründung: Dies ist ein Testsignal für Demonstrationszwecke."""

def log_market_conditions(close):
    df = pd.DataFrame({'close': close})
    df['sma_short'] = df['close'].rolling(window=SHORT_SMA_PERIOD).mean()
    df['sma_long'] = df['close'].rolling(window=LONG_SMA_PERIOD).mean()
    df['ema_short'] = df['close'].ewm(span=SHORT_SMA_PERIOD, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=LONG_SMA_PERIOD, adjust=False).mean()
    
    # Calculate RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Calculate MACD
    df['ema_fast'] = df['close'].ewm(span=MACD_FAST, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=MACD_SLOW, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal_line'] = df['macd'].ewm(span=MACD_SIGNAL, adjust=False).mean()
    
    logger.info(f"Aktueller Preis: {close[-1]:.2f}")
    logger.info(f"{SHORT_SMA_PERIOD}-Perioden SMA: {df['sma_short'].iloc[-1]:.2f}")
    logger.info(f"{LONG_SMA_PERIOD}-Perioden SMA: {df['sma_long'].iloc[-1]:.2f}")
    logger.info(f"{SHORT_SMA_PERIOD}-Perioden EMA: {df['ema_short'].iloc[-1]:.2f}")
    logger.info(f"{LONG_SMA_PERIOD}-Perioden EMA: {df['ema_long'].iloc[-1]:.2f}")
    logger.info(f"RSI: {df['rsi'].iloc[-1]:.2f}")
    logger.info(f"MACD: {df['macd'].iloc[-1]:.2f}")
    logger.info(f"MACD Signal Line: {df['signal_line'].iloc[-1]:.2f}")

async def send_telegram_message_async(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message)
        logger.info(f"Telegram-Nachricht gesendet: {message}")
    except Exception as e:
        logger.error(f"Fehler beim Senden der Telegram-Nachricht: {e}")

def send_telegram_message(message):
    asyncio.run(send_telegram_message_async(message))

def cleanup():
    mt5.shutdown()
    logger.info("MetaTrader5 Verbindung beendet")

def main(force_test_signal=False):
    initialize_mt5()
    try:
        while True:
            logger.info("Abrufen der aktuellen XAUUSD-Preisdaten...")
            close = get_xauusd_price()
            if close is not None:
                log_market_conditions(close)
                logger.info("Generiere Signal basierend auf den Preisdaten...")
                
                if force_test_signal:
                    signal = generate_test_signal()
                    logger.info("Testsignal generiert.")
                else:
                    signal = generate_signal(close)
                
                if signal:
                    logger.info("Signal generiert. Sende an Telegram...")
                    send_telegram_message(signal)
                    logger.info(f"Signal gesendet: {signal}")
                else:
                    logger.info("Kein Signal generiert. Warte auf nächste Überprüfung.")
            else:
                logger.warning("Konnte keine Preisdaten abrufen. Überspringe diesen Zyklus.")
            
            logger.info(f"Warte {CHECK_INTERVAL} Sekunden bis zur nächsten Überprüfung...")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Programm manuell beendet")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")
    finally:
        cleanup()

def test_run():
    initialize_mt5()
    try:
        close = get_xauusd_price()
        if close is not None:
            log_market_conditions(close)
            real_signal = generate_signal(close)
            if real_signal:
                print(f"Echtes Signal generiert: {real_signal}")
                send_telegram_message(f"ECHT: {real_signal}")
            else:
                print("Kein echtes Signal generiert.")
        
        test_signal = generate_test_signal()
        print(f"Testsignal generiert: {test_signal}")
        send_telegram_message(f"TEST: {test_signal}")
    finally:
        cleanup()

def backtest(days=30):
    symbol = "XAUUSD"
    timeframe = mt5.TIMEFRAME_M15
    current_time = mt5.symbol_info_tick(symbol).time
    from_date = current_time - days * 24 * 60 * 60  # days in seconds
    rates = mt5.copy_rates_range(symbol, timeframe, from_date, current_time)
    
    if rates is None or len(rates) == 0:
        logger.error("Fehler beim Abrufen der historischen Daten für Backtesting")
        return
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    close = df['close'].values
    
    signals = []
    for i in range(LONG_SMA_PERIOD, len(close)):
        signal = generate_signal(close[:i])
        if signal:
            signals.append((df['time'].iloc[i], signal))
    
    logger.info(f"Backtesting Ergebnis für die letzten {days} Tage:")
    logger.info(f"Anzahl der generierten Signale: {len(signals)}")
    for time, signal in signals:
        logger.info(f"Zeit: {time}, Signal: {signal}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            test_run()
        elif sys.argv[1] == "--telegram-test":
            send_telegram_message("Dies ist eine Testnachricht von Ihrem Forex-Signalgenerator.")
        elif sys.argv[1] == "--force-signal":
            main(force_test_signal=True)
    else:
        main()
