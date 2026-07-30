import {
  createElement,
  useMemo,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";

import type { Candle } from "../types";

export const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"];

type ButtonVariant = "primary" | "secondary" | "danger" | "refresh" | "paper";

const BUTTON_CLASSES: Record<ButtonVariant, string> = {
  primary: "primary-action",
  secondary: "secondary-action",
  danger: "emergency",
  refresh: "refresh",
  paper: "paper-enable-button",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

export function Button({
  variant = "secondary",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  const classes = [BUTTON_CLASSES[variant], className]
    .filter(Boolean)
    .join(" ");
  return <button className={classes} type={type} {...props} />;
}

type CardProps = HTMLAttributes<HTMLElement> & {
  as?: "article" | "section" | "div";
};

export function Card({ as = "article", className = "", ...props }: CardProps) {
  return createElement(as, {
    ...props,
    className: ["panel", className].filter(Boolean).join(" "),
  });
}

export function Badge({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={["badge", className].filter(Boolean).join(" ")}>
      {children}
    </span>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="empty-state">{children}</p>;
}

export function LoadingState({
  children = "Laddar…",
}: {
  children?: ReactNode;
}) {
  return (
    <p className="loading-state" role="status">
      {children}
    </p>
  );
}

export function ErrorState({ children }: { children: ReactNode }) {
  return (
    <p className="error-state" role="alert">
      {children}
    </p>
  );
}

type IntervalSelectorProps = {
  intervals?: string[];
  value: string;
  onChange: (interval: string) => void;
};

export function IntervalSelector({
  intervals = INTERVALS,
  value,
  onChange,
}: IntervalSelectorProps) {
  return (
    <div className="intervals">
      {intervals.map((interval) => (
        <button
          key={interval}
          className={value === interval ? "active" : ""}
          onClick={() => onChange(interval)}
          type="button"
        >
          {interval}
        </button>
      ))}
    </div>
  );
}

export function PriceChart({ candles }: { candles: Candle[] }) {
  const points = useMemo(() => {
    if (!candles.length) return "";
    const closes = candles.map((candle) => candle.close);
    const minimum = Math.min(...closes);
    const range = Math.max(...closes) - minimum || 1;

    return closes
      .map(
        (close, index) =>
          `${(index / Math.max(closes.length - 1, 1)) * 1000},${
            260 - ((close - minimum) / range) * 220
          }`,
      )
      .join(" ");
  }, [candles]);

  return (
    <div className="chart">
      <svg viewBox="0 0 1000 300" preserveAspectRatio="none">
        <defs>
          <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#d8a849" stopOpacity=".32" />
            <stop offset="100%" stopColor="#d8a849" stopOpacity="0" />
          </linearGradient>
        </defs>
        {points && (
          <>
            <polygon points={`0,300 ${points} 1000,300`} fill="url(#area)" />
            <polyline
              points={points}
              fill="none"
              stroke="#e0b458"
              strokeWidth="3"
              vectorEffect="non-scaling-stroke"
            />
          </>
        )}
      </svg>
    </div>
  );
}
