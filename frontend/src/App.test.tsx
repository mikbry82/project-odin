import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const apiMock = vi.hoisted(() => ({
  getStatus: vi.fn(),
  getMarkets: vi.fn(),
  getPortfolio: vi.fn(),
  getScanner: vi.fn(),
  getAutoSettings: vi.fn(),
  getPerformance: vi.fn(),
  getStrategies: vi.fn(),
  getExchangeConnection: vi.fn(),
  getLiveRisk: vi.fn(),
  getTradingPairs: vi.fn(),
  getLiveAccount: vi.fn(),
  saveLiveRisk: vi.fn(),
  previewLiveOrder: vi.fn(),
  activateLiveKillSwitch: vi.fn(),
}));

vi.mock("./api", () => ({ api: apiMock }));

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("expertMode", "false");
  localStorage.setItem("simpleMode", "true");
  apiMock.getStatus.mockResolvedValue({
    trading_mode: "off",
    operating_mode: "simulation",
    emergency_stop: false,
    live_trading_available: false,
  });
  apiMock.getMarkets.mockResolvedValue({ markets: [] });
  apiMock.getPortfolio.mockResolvedValue(null);
  apiMock.getScanner.mockResolvedValue({ items: [] });
  apiMock.getAutoSettings.mockResolvedValue({ enabled: false });
  apiMock.getPerformance.mockResolvedValue(null);
  apiMock.getStrategies.mockResolvedValue([]);
  apiMock.getExchangeConnection.mockResolvedValue({
    provider: "kraken",
    status: "disconnected",
  });
  apiMock.getLiveRisk.mockResolvedValue({
    max_order_eur: 100,
    max_daily_eur: 300,
    max_orders_daily: 3,
    daily_loss_eur: 100,
    cooldown_seconds: 300,
    allowed_pairs: ["BTC/EUR", "ETH/EUR"],
    pair_limits: [],
    buy_only: true,
    risk_warning_accepted: false,
    kill_switch_active: false,
  });
  apiMock.getTradingPairs.mockResolvedValue({
    pairs: [
      {
        exchange_pair_id: "XXBTZEUR",
        symbol: "BTC/EUR",
        base_asset_id: "XXBT",
        base_symbol: "BTC",
        quote_asset_id: "ZEUR",
        quote_symbol: "EUR",
        minimum_quantity: 0.0001,
        minimum_cost: 5,
        price_decimals: 1,
        quantity_decimals: 8,
        status: "online",
        tradable: true,
        allowed: true,
      },
      {
        exchange_pair_id: "XETHZEUR",
        symbol: "ETH/EUR",
        base_asset_id: "XETH",
        base_symbol: "ETH",
        quote_asset_id: "ZEUR",
        quote_symbol: "EUR",
        minimum_quantity: 0.001,
        minimum_cost: 5,
        price_decimals: 2,
        quantity_decimals: 8,
        status: "online",
        tradable: true,
        allowed: true,
      },
      {
        exchange_pair_id: "ADAEUR",
        symbol: "ADA/EUR",
        base_asset_id: "ADA",
        base_symbol: "ADA",
        quote_asset_id: "ZEUR",
        quote_symbol: "EUR",
        minimum_quantity: 10,
        minimum_cost: 5,
        price_decimals: 5,
        quantity_decimals: 8,
        status: "cancel_only",
        tradable: false,
        allowed: false,
      },
    ],
  });
  apiMock.getLiveAccount.mockResolvedValue({
    connection_status: "connected",
    last_successful_refresh: "2026-07-30T20:00:00Z",
    total_estimated_eur: 100,
    available_eur: 50,
    valuation_is_estimate: true,
    balances: [
      {
        canonical_asset_id: "XXBT",
        display_symbol: "BTC",
        total: 0.001,
        available: 0.0008,
        reserved: 0.0002,
        estimated_eur_value: 50,
        allocation_percent: 50,
        pricing_status: "direct",
        price_timestamp: "2026-07-30T20:00:00Z",
        average_acquisition_price_eur: null,
        estimated_unrealized_pnl_eur: null,
      },
      {
        canonical_asset_id: "UNKNOWN.S",
        display_symbol: "UNKNOWN.S",
        total: 1,
        available: 1,
        reserved: 0,
        estimated_eur_value: null,
        allocation_percent: null,
        pricing_status: "unpriced",
        price_timestamp: null,
        average_acquisition_price_eur: null,
        estimated_unrealized_pnl_eur: null,
      },
    ],
    open_orders: [],
    recent_orders: [],
    recent_fills: [],
  });
  apiMock.saveLiveRisk.mockImplementation(async (value) => value);
  apiMock.previewLiveOrder.mockResolvedValue({
    preview_id: "preview",
    exchange: "kraken",
    symbol: "BTC/EUR",
    side: "buy",
    order_type: "market",
    requested_amount: 10,
    estimated_quantity: 0.0002,
    current_market_price: 50000,
    limit_price: null,
    estimated_total: 10,
    estimated_fee: 0.04,
    maximum_order_eur: 100,
    minimum_quantity: 0.0001,
    minimum_cost: 5,
    quantity_decimals: 8,
    price_decimals: 1,
    pair_status: "online",
    price_timestamp: "2026-07-30T20:00:00Z",
    available_eur: 50,
    available_crypto: null,
    available_crypto_after: null,
    sell_percentage: null,
    estimated_gross_proceeds: null,
    estimated_net_proceeds: null,
    max_slippage_percent: 1,
    estimated_price_low: 49500,
    estimated_price_high: 50500,
    applied_risk_limits: {},
    warnings: ["Riktiga pengar kommer att användas."],
    expires_at: "2026-07-30T20:00:30Z",
  });
});

describe("complete interface", () => {
  it("always renders advanced navigation and no interface-level toggle", () => {
    render(<App />);

    expect(
      screen.getByRole("button", { name: "Market Scanner" }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Strategy Lab" })).toBeVisible();
    expect(screen.queryByText(/Expertläge/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Enkel svenska/i)).not.toBeInTheDocument();
  });

  it("old stored preferences cannot hide advanced fields", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Inställningar/i }));

    expect(await screen.findByLabelText("Högst per order (EUR)")).toBeVisible();
    expect(screen.getByLabelText("Högst per dag (EUR)")).toBeVisible();
    expect(screen.getByLabelText("Daglig förlustgräns (EUR)")).toBeVisible();
    expect(screen.getByLabelText("Säkerhetspaus (sekunder)")).toBeVisible();
    expect(localStorage.getItem("expertMode")).toBeNull();
    expect(localStorage.getItem("simpleMode")).toBeNull();
  });

  it("retains live-trading safeguards without enabling live trading", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Inställningar/i }));

    expect(
      await screen.findByText(/riktiga pengar kan förloras/i),
    ).toBeVisible();
    expect(screen.getByLabelText("Skriv JAG FÖRSTÅR RISKEN")).toBeVisible();
    expect(screen.getByRole("button", { name: "NÖDSTOPP LIVE" })).toBeVisible();
    expect(screen.queryByText("Skapa förhandsvisning")).not.toBeInTheDocument();
    expect(apiMock.activateLiveKillSwitch).not.toHaveBeenCalled();
  });

  it("shows estimated values and keeps unknown unpriced assets visible", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Livekonto" }));

    expect((await screen.findAllByText("UNKNOWN.S"))[0]).toBeVisible();
    expect(screen.getByText("Värde saknas")).toBeVisible();
    expect(
      screen.getByText("Uppskattning, inte ett exakt realisationsvärde"),
    ).toBeVisible();
    expect(screen.getByText("Inga öppna spotordrar.")).toBeVisible();
  });

  it("uses a searchable active-pair multi-select with migrated defaults", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Livekonto" }));
    fireEvent.click(await screen.findByRole("button", { name: "2 valda" }));

    expect(screen.getByText("BTC/EUR ×")).toBeVisible();
    expect(screen.getByText("ETH/EUR ×")).toBeVisible();
    expect(
      screen.queryByText(/ADA\/EUR · cancel_only/),
    ).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Sök kryptovaluta"), {
      target: { value: "Ethereum" },
    });
    expect(screen.getByText("Ethereum")).toBeVisible();
    expect(screen.getByText(/ETH\/EUR/, { selector: "span" })).toBeVisible();
  });

  it("removes and restores allowed pairs through the backend API", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Livekonto" }));
    fireEvent.click(await screen.findByRole("button", { name: "2 valda" }));
    fireEvent.click(screen.getByRole("button", { name: "Rensa" }));
    fireEvent.click(screen.getByRole("button", { name: "Återställ standard" }));
    fireEvent.click(screen.getByText("BTC/EUR ×"));
    fireEvent.click(screen.getByRole("button", { name: "Spara urval" }));

    expect(apiMock.saveLiveRisk).toHaveBeenCalledWith(
      expect.objectContaining({ allowed_pairs: ["ETH/EUR"] }),
    );
  });

  it("previews a manual buy and changed input invalidates it", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Livekonto" }));
    const amount = await screen.findByLabelText("Orderbelopp");
    fireEvent.change(amount, { target: { value: "10" } });
    fireEvent.click(
      screen.getByRole("button", { name: "Förhandsgranska köp" }),
    );
    expect(await screen.findByText("DETTA ÄR EN RIKTIG ORDER")).toBeVisible();
    expect(apiMock.previewLiveOrder).toHaveBeenCalledWith(
      expect.objectContaining({ symbol: "BTC/EUR", amount_eur: 10 }),
    );
    fireEvent.change(amount, { target: { value: "11" } });
    expect(
      screen.queryByText("DETTA ÄR EN RIKTIG ORDER"),
    ).not.toBeInTheDocument();
  });

  it("previews a limit buy entered as cryptocurrency quantity", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Livekonto" }));
    fireEvent.change(await screen.findByLabelText("Ordertyp"), {
      target: { value: "limit" },
    });
    fireEvent.change(screen.getByLabelText("Inmatningssätt"), {
      target: { value: "crypto" },
    });
    fireEvent.change(screen.getByLabelText("Orderbelopp"), {
      target: { value: "0.001" },
    });
    fireEvent.change(screen.getByLabelText("Limitpris"), {
      target: { value: "49000" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Förhandsgranska köp" }),
    );

    expect(apiMock.previewLiveOrder).toHaveBeenCalledWith(
      expect.objectContaining({
        order_type: "limit",
        amount_crypto: 0.001,
        limit_price: 49000,
      }),
    );
  });

  it("offers held available assets only and previews a 100 percent sell", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Livekonto" }));
    fireEvent.change(await screen.findByLabelText("Ordersida"), {
      target: { value: "sell" },
    });

    const assetSelect = screen.getByLabelText("Kryptovaluta");
    expect(assetSelect).toHaveValue("BTC/EUR");
    expect(
      screen.queryByRole("option", { name: "ETH/EUR" }),
    ).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Inmatningssätt"), {
      target: { value: "percentage" },
    });
    fireEvent.click(screen.getByRole("button", { name: "100 %" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Förhandsgranska försäljning" }),
    );

    expect(apiMock.previewLiveOrder).toHaveBeenCalledWith(
      expect.objectContaining({
        symbol: "BTC/EUR",
        side: "sell",
        sell_percentage: 100,
      }),
    );
  });
});
