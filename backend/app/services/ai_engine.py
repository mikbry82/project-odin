from __future__ import annotations

from dataclasses import dataclass

from app.services.indicators import analyse


@dataclass(frozen=True)
class PortfolioContext:
    equity: float = 100000.0
    cash_balance: float = 100000.0
    open_positions: int = 0
    max_open_positions: int = 3
    symbol_already_open: bool = False


def _clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, round(value)))


def _verdict(score: int) -> str:
    if score >= 80:
        return "STARKT KÖP"
    if score >= 65:
        return "KÖP"
    if score <= 20:
        return "STARKT SÄLJ"
    if score <= 35:
        return "SÄLJ"
    return "AVVAKTA"


def _agent(
    agent: str,
    title: str,
    verdict: str,
    score: int,
    confidence: int,
    summary: str,
    evidence: list[str],
    warnings: list[str] | None = None,
    status: str = "AKTIV",
) -> dict:
    return {
        "agent": agent,
        "title": title,
        "verdict": verdict,
        "score": _clamp(score),
        "confidence": _clamp(confidence, 0, 95),
        "status": status,
        "summary": summary,
        "evidence": evidence,
        "warnings": warnings or [],
    }


def run_ai_engine(
    candles: list[dict],
    portfolio: PortfolioContext | None = None,
) -> dict:
    """Explainable local multi-agent engine.

    This version deliberately uses transparent deterministic models rather than
    claiming to be a trained language model. News and macro agents stay offline
    until verified data sources are connected.
    """
    portfolio = portfolio or PortfolioContext()
    indicators = analyse(candles)
    closes = [float(c["close"]) for c in candles]
    volumes = [float(c.get("volume", 0.0)) for c in candles]
    price = closes[-1]

    # Technical Analyst
    technical_score = indicators["total_score"]
    technical_evidence = list(indicators["explanation"])
    technical = _agent(
        "technical",
        "Technical Analyst",
        indicators["signal"],
        technical_score,
        indicators["confidence"],
        indicators["simple_explanation"],
        technical_evidence,
        list(indicators["warnings"]),
    )

    # Market Regime Analyst: trend consistency and participation.
    lookback = min(24, len(closes) - 1)
    change_pct = ((price / closes[-lookback - 1]) - 1) * 100 if lookback > 0 else 0.0
    recent_volumes = volumes[-20:] if len(volumes) >= 20 else volumes
    baseline_volumes = (
        volumes[-40:-20]
        if len(volumes) >= 40
        else volumes[: -len(recent_volumes)] or recent_volumes
    )
    recent_volume = sum(recent_volumes) / max(1, len(recent_volumes))
    baseline_volume = sum(baseline_volumes) / max(1, len(baseline_volumes))
    volume_ratio = recent_volume / baseline_volume if baseline_volume else 1.0
    regime_score = 50 + max(-25, min(25, change_pct * 4))
    if volume_ratio >= 1.15:
        regime_score += 12 if change_pct >= 0 else -12
    elif volume_ratio <= 0.75:
        regime_score -= 8
    regime_score = _clamp(regime_score)
    regime_evidence = [
        f"Prisförändring över de senaste {lookback} ljusen: {change_pct:+.2f} %.",
        f"Senaste volymnivån är {volume_ratio:.2f}× jämförelseperioden.",
    ]
    regime_warnings: list[str] = []
    if abs(change_pct) >= 10:
        regime_warnings.append(
            "Marknaden har redan gjort en stor rörelse; risken för rekyl är högre."
        )
    regime = _agent(
        "regime",
        "Market Regime Analyst",
        _verdict(regime_score),
        regime_score,
        62 + min(25, abs(regime_score - 50)),
        (
            "Marknadsläget stödjer den tekniska riktningen."
            if (regime_score >= 60 and technical_score >= 60)
            or (regime_score <= 40 and technical_score <= 40)
            else "Marknadsläget ger inte en tydlig bekräftelse."
        ),
        regime_evidence,
        regime_warnings,
    )

    # Risk Manager: high score means trade is safe enough, not bullish.
    atr = float(indicators["atr_14"] or 0.0)
    atr_pct = atr / price * 100 if price else 0.0
    rsi = float(indicators["rsi_14"] or 50.0)
    risk_score = 92
    risk_warnings: list[str] = []
    if atr_pct >= 6:
        risk_score -= 55
        risk_warnings.append("Extrem volatilitet enligt ATR.")
    elif atr_pct >= 4:
        risk_score -= 38
        risk_warnings.append("Hög volatilitet kräver mindre position.")
    elif atr_pct >= 2:
        risk_score -= 18
    if rsi >= 75 or rsi <= 25:
        risk_score -= 20
        risk_warnings.append("RSI befinner sig i ett extremområde.")
    if abs(change_pct) >= 12:
        risk_score -= 15
    risk_score = _clamp(risk_score)
    risk_level = "LÅG" if risk_score >= 75 else "MEDEL" if risk_score >= 50 else "HÖG"
    risk = _agent(
        "risk",
        "Risk Manager",
        f"{risk_level} RISK",
        risk_score,
        88,
        (
            "Risknivån tillåter normal paper-position."
            if risk_level == "LÅG"
            else "Positionen bör minskas och skyddas med tydlig stop-loss."
            if risk_level == "MEDEL"
            else "Ny position bör undvikas tills risken sjunker."
        ),
        [
            f"ATR motsvarar {atr_pct:.2f} % av priset.",
            f"RSI ligger på {rsi:.1f}.",
        ],
        risk_warnings,
    )

    # Portfolio Manager.
    capacity_ratio = portfolio.cash_balance / portfolio.equity if portfolio.equity > 0 else 0
    portfolio_score = 90
    portfolio_warnings: list[str] = []
    if portfolio.symbol_already_open:
        portfolio_score = 20
        portfolio_warnings.append("Det finns redan en öppen position i marknaden.")
    elif portfolio.open_positions >= portfolio.max_open_positions:
        portfolio_score = 15
        portfolio_warnings.append("Maximalt antal öppna positioner är uppnått.")
    elif capacity_ratio < 0.1:
        portfolio_score = 30
        portfolio_warnings.append("Mindre än 10 % av portföljvärdet finns som tillgängligt saldo.")
    elif capacity_ratio < 0.3:
        portfolio_score = 60
    portfolio_score = _clamp(portfolio_score)
    portfolio_agent = _agent(
        "portfolio",
        "Portfolio Manager",
        "OK" if portfolio_score >= 65 else "BEGRÄNSA" if portfolio_score >= 40 else "STOPP",
        portfolio_score,
        90,
        (
            "Portföljen har utrymme för en ny position."
            if portfolio_score >= 65
            else "Portföljexponeringen begränsar nya affärer."
        ),
        [
            f"Öppna positioner: {portfolio.open_positions}/{portfolio.max_open_positions}.",
            f"Tillgängligt saldo: {capacity_ratio * 100:.1f} % av portföljvärdet.",
        ],
        portfolio_warnings,
    )

    # Offline agents are shown honestly and excluded from the weighted decision.
    news = _agent(
        "news",
        "News Analyst",
        "EJ ANSLUTEN",
        50,
        0,
        "Nyhetsdata är inte ansluten i v0.7.0 och påverkar därför inte beslutet.",
        [],
        ["Koppla en verifierad nyhetskälla innan nyhetssentiment används."],
        status="OFFLINE",
    )
    macro = _agent(
        "macro",
        "Macro Analyst",
        "EJ ANSLUTEN",
        50,
        0,
        "Makrodata är inte ansluten i v0.7.0 och påverkar därför inte beslutet.",
        [],
        ["Räntor, inflation och dollarindex ingår ännu inte."],
        status="OFFLINE",
    )

    # Chief AI combines direction with risk/portfolio gates.
    directional_score = technical_score * 0.68 + regime_score * 0.32
    gate = min(1.0, risk_score / 70) * min(1.0, portfolio_score / 70)
    chief_score = _clamp(50 + (directional_score - 50) * gate)

    if risk_score < 40 or portfolio_score < 40:
        chief_verdict = "AVVAKTA"
    else:
        chief_verdict = _verdict(chief_score)

    agreement = 100 - abs(technical_score - regime_score)
    chief_confidence = _clamp(
        45 + abs(chief_score - 50) * 0.7 + agreement * 0.2,
        45,
        95,
    )
    if news["status"] == "OFFLINE" or macro["status"] == "OFFLINE":
        chief_confidence = min(chief_confidence, 88)

    base_position = 2.0
    conviction_multiplier = max(0.0, (chief_score - 50) / 30)
    risk_multiplier = risk_score / 100
    portfolio_multiplier = portfolio_score / 100
    position_size = base_position * conviction_multiplier * risk_multiplier * portfolio_multiplier
    position_size = max(0.0, min(5.0, round(position_size, 2)))
    if chief_verdict not in {"KÖP", "STARKT KÖP"}:
        position_size = 0.0

    reasons = [
        f"Technical Analyst: {technical['verdict']} ({technical_score}/100).",
        f"Market Regime Analyst: {regime['verdict']} ({regime_score}/100).",
        f"Risk Manager: {risk['verdict']} ({risk_score}/100).",
        f"Portfolio Manager: {portfolio_agent['verdict']} ({portfolio_score}/100).",
    ]
    warnings = [
        *technical["warnings"],
        *regime["warnings"],
        *risk["warnings"],
        *portfolio_agent["warnings"],
    ]
    if news["status"] == "OFFLINE":
        warnings.append("Chief AI saknar nyhetssentiment.")
    if macro["status"] == "OFFLINE":
        warnings.append("Chief AI saknar makrodata.")

    chief_summary = {
        "STARKT KÖP": (
            "Flera aktiva analysmoduler är tydligt positiva och riskspärrarna "
            "tillåter en paper-position."
        ),
        "KÖP": "Helhetsbilden är positiv, men positionen bör hållas kontrollerad.",
        "AVVAKTA": "Underlaget är blandat eller en riskspärr begränsar affären.",
        "SÄLJ": "Helhetsbilden är negativ och talar för att minska exponering.",
        "STARKT SÄLJ": "Flera aktiva analysmoduler är tydligt negativa.",
    }[chief_verdict]

    return {
        "agents": [technical, regime, risk, portfolio_agent, news, macro],
        "chief": {
            "verdict": chief_verdict,
            "score": chief_score,
            "confidence": chief_confidence,
            "risk_level": risk_level,
            "position_size_percent": position_size,
            "summary": chief_summary,
            "reasons": reasons,
            "warnings": list(dict.fromkeys(warnings)),
        },
    }
