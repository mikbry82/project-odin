# Project Odin v0.7.0 — Explainable AI Engine

v0.7 bygger vidare på den fungerande Market Scanner och automatiska paper-handeln.

## Nytt

- **AI Center** med flera specialiserade analysmoduler
- **Technical Analyst** för EMA, RSI, MACD och ATR
- **Market Regime Analyst** för trend, prisförändring och volymdeltagande
- **Risk Manager** som fungerar som säkerhetsspärr
- **Portfolio Manager** som kontrollerar saldo, dubbelexponering och positionsgräns
- **Chief AI** som väger ihop aktiva agenters bedömningar
- Chief AI-signal, confidence, risknivå och föreslagen portföljandel
- Market Scanner och Auto Paper använder nu Chief AI:s beslut
- AI-motivering sparas i handelsjournalen

## Viktig transparens

v0.7 använder en **lokal, regelbaserad och förklarbar multi-agentmotor**. Den låtsas inte vara en tränad språkmodell.

News Analyst och Macro Analyst visas i gränssnittet men står tydligt som **EJ ANSLUTEN**. De påverkar inte beslutet förrän verifierade nyhets- och makrodatakällor har lagts till.

## Installation

Stoppa den gamla versionen och kopiera innehållet över din befintliga projektmapp.

```powershell
docker compose down
docker compose up --build
```

Öppna:

```text
http://localhost:5173
```

## Testa

1. Öppna **AI Center**.
2. Välj marknad och tidsram.
3. Kontrollera Chief AI och varje agents underlag.
4. Aktivera Paper Trading.
5. Starta Auto Paper i Market Scanner.

Endast paper trading stöds. Livehandel är fortfarande låst.

## v0.8.0 – Strategy Engine, Sprint 1

Nyheter:

- Strategy Lab i gränssnittet.
- Strategier lagras i PostgreSQL.
- En aktiv strategi åt gången.
- Kopiering och versionsökning vid varje sparning.
- Konfigurerbara RSI-, MACD- och poängregler.
- Separat riskprofil per strategi.
- Direkt utvärdering mot vald marknad och tidsram.
- Deterministiska tester för strategimotorn.

Backtesting är fortfarande låst och planeras till nästa sprint.

## v0.8.1 – Enkel användarupplevelse

- Ny nybörjarvänlig startsida med marknadsläge, bästa möjlighet och testkonto.
- Förenklad meny: Hem, Marknaden, Mitt testkonto, Odins råd, Resultat och Inställningar.
- Expertverktyg döljs som standard och kan aktiveras i Inställningar.
- Paper Trading heter nu Testkonto i det enkla gränssnittet.
- Tydligare autopilotstatus och vanliga svenska förklaringar.
- Automatisk riktig handel är fortsatt låst.
