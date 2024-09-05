# Forex XAU/USD Signalgenerator

## Projektbeschreibung
Dieses Projekt implementiert einen fortschrittlichen, automatisierten Signalgenerator für den Forex-Markt, speziell für das XAU/USD (Gold/US-Dollar) Währungspaar. Es analysiert Marktdaten in Echtzeit, generiert präzise Kauf- und Verkaufssignale basierend auf mehreren technischen Indikatoren und sendet diese an eine Telegram-Gruppe.

## Funktionen
- Echtzeit-Datenabfrage für XAU/USD über MetaTrader5
- Erweiterte technische Analyse zur Signalgenerierung, einschließlich:
  - Simple Moving Average (SMA)
  - Exponential Moving Average (EMA)
  - Relative Strength Index (RSI)
  - Moving Average Convergence Divergence (MACD)
  - Average True Range (ATR) für dynamische Take-Profit und Stop-Loss-Berechnung
- Automatisches Senden von detaillierten Handelssignalen an eine Telegram-Gruppe
- Kontinuierliche Überwachung und Aktualisierung in konfigurierbaren Intervallen
- Dynamische Anpassung von Take-Profit und Stop-Loss basierend auf Marktvolatilität

## Technische Anforderungen
- Python 3.8+
- MetaTrader5 (für Marktdatenzugriff)
- pandas (für Datenmanipulation und technische Indikatoren)
- python-telegram-bot (für Telegram-Integration)

## Installation
1. Klonen Sie das Repository:
   ```bash
   git clone https://github.com/yourusername/forex-xauusd-signal-generator.git
   cd forex-xauusd-signal-generator
   ```
2. Erstellen Sie eine virtuelle Umgebung und aktivieren Sie sie:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Für Windows: venv\Scripts\activate
   ```
3. Installieren Sie die erforderlichen Pakete:
   ```bash
   pip install -r requirements.txt
   ```

## Konfiguration
1. Öffnen Sie die `config.py` Datei und passen Sie die folgenden Einstellungen an:
   - MetaTrader5 Zugangsdaten (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
   - Telegram-Bot-Token und Chat-ID
   - Technische Indikator-Parameter (SMA, EMA, RSI, MACD, ATR)
   - Take-Profit und Stop-Loss Einstellungen

## Verwendung
1. Starten Sie das Hauptskript:
   ```bash
   python main.py
   ```
2. Für einen Testlauf mit simulierten Signalen:
   ```bash
   python main.py --test
   ```
3. Für einen einmaligen Telegram-Test:
   ```bash
   python main.py --telegram-test
   ```

## Erweiterte Funktionen
- Backtesting: Testen Sie Ihre Strategie mit historischen Daten
- Dynamische TP/SL: Automatische Anpassung basierend auf Marktvolatilität
- Multi-Timeframe-Analyse: Verbesserte Signalgenauigkeit durch Betrachtung verschiedener Zeitrahmen

## Beitrag
Beiträge zum Projekt sind willkommen! Bitte erstellen Sie einen Pull Request oder öffnen Sie ein Issue für Vorschläge und Verbesserungen.

## Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert. Siehe die LICENSE-Datei für Details.

## Haftungsausschluss
Dieses Tool dient nur zu Bildungszwecken. Handeln Sie auf eigenes Risiko. Der Autor übernimmt keine Verantwortung für finanzielle Verluste, die durch die Verwendung dieses Tools entstehen können.
