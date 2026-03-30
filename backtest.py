# ══════════════════════════════════════════════════════════════════════
#  research/backtest.py  —  бэктест, grid search, walk-forward
#
#  Запуск из корня репозитория:
#    python research/backtest.py
#
#  Результаты:
#    grid_search_results.csv
#    walk_forward_results.csv
#    grid_search_chart.png
#    walk_forward_chart.png
# ══════════════════════════════════════════════════════════════════════

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from strategy.indicators import prepare_data

# ── Конфигурация ───────────────────────────────────────────────────────
SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AMD", "NFLX", "INTC",
]
INITIAL_CAPITAL = 10_000
MIN_TRADES      = 5

PARAM_GRID = {
    "risk_per_trade":     [0.01, 0.02],
    "trailing_atr_mult":  [1.0, 1.5, 2.0],
    "volume_filter_mult": [1.1, 1.2, 1.5],
    "max_positions":      [3, 5],
    "rsi_low":            [55, 60],
    "rsi_high":           [70, 75],
}

WF_TRAIN_MONTHS = 18
WF_TEST_MONTHS  = 6


# ══════════════════════════════════════════════════════════════════════
#  СИГНАЛЫ (локальные копии без импорта exchange)
# ══════════════════════════════════════════════════════════════════════

def _check_buy(data: pd.DataFrame, i: int, params: dict) -> bool:
    row      = data.iloc[i]
    prev_row = data.iloc[i - 1]
    close    = row["Close"]

    if any(pd.isna(v) for v in [close, row["MA50"], row["MA200"], row["RSI"],
                                  row["MACD"], row["MACD_sig"],
                                  prev_row["MACD"], prev_row["MACD_sig"]]):
        return False

    macd_cross = (
        row["MACD"]      > row["MACD_sig"] and
        prev_row["MACD"] <= prev_row["MACD_sig"]
    )
    return (
        close > row["MA50"]                                              and
        row["MA50"]  > row["MA200"]                                      and
        params["rsi_low"] < row["RSI"] < params["rsi_high"]             and
        close > prev_row["Close"]                                        and
        row["Volume"] > row["Volume_MA"] * params["volume_filter_mult"]  and
        macd_cross
    )


def _check_sell(row: pd.Series, entry: dict) -> bool:
    close = row["Close"]
    if any(pd.isna(v) for v in [close, row["MA50"], row["RSI"]]):
        return False
    return (
        close <= entry["stop"] or
        close >= entry["take"] or
        close <  row["MA50"]   or
        row["RSI"] < 50
    )


def _market_filter(spy_data: pd.DataFrame, date) -> bool:
    if date not in spy_data.index:
        return False
    spy = spy_data.loc[date]
    return (
        not pd.isna(spy["MA200"]) and spy["Close"] > spy["MA200"] and
        not pd.isna(spy["MA50_slope"]) and spy["MA50_slope"] > 0   and
        not pd.isna(spy["MA50"])  and spy["Close"] > spy["MA50"]
    )


# ══════════════════════════════════════════════════════════════════════
#  ОДИН ПРОГОН БЭКТЕСТА
# ══════════════════════════════════════════════════════════════════════

def run_backtest(all_data: dict, spy_data: pd.DataFrame,
                 params: dict) -> dict | None:
    capital   = float(INITIAL_CAPITAL)
    portfolio = {}
    trade_log = []

    for symbol, data in all_data.items():
        for i in range(1, len(data)):
            row  = data.iloc[i]
            date = row.name

            if not _market_filter(spy_data, date):
                continue

            # Выход
            if symbol in portfolio:
                entry = portfolio[symbol]
                # Трейлинг стоп
                new_stop = row["Close"] - params["trailing_atr_mult"] * row["ATR"]
                if new_stop > entry["stop"]:
                    entry["stop"] = new_stop

                if _check_sell(row, entry):
                    profit   = (row["Close"] - entry["entry_price"]) * entry["size"]
                    capital += profit
                    trade_log.append({
                        "date":    date,
                        "profit":  profit,
                        "capital": capital,
                    })
                    del portfolio[symbol]

            # Вход
            elif _check_buy(data, i, params):
                if len(portfolio) >= params["max_positions"]:
                    continue
                ep   = row["Close"]
                stop = ep - 1.5 * row["ATR"]
                take = ep + 3.0 * (ep - stop)
                risk = ep - stop
                if risk <= 0:
                    continue
                size = (capital * params["risk_per_trade"]) / risk
                portfolio[symbol] = {
                    "entry_date":  date,
                    "entry_price": ep,
                    "stop": stop, "take": take, "size": size,
                }

    if len(trade_log) < MIN_TRADES:
        return None

    profits      = [t["profit"] for t in trade_log]
    wins         = [p for p in profits if p > 0]
    losses       = [p for p in profits if p < 0]
    total_return = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    win_rate     = len(wins) / len(profits) * 100

    if losses:
        pf = min(abs(sum(wins) / sum(losses)), 10.0)
    elif wins:
        pf = 10.0
    else:
        pf = 0.0

    equity = [INITIAL_CAPITAL] + [t["capital"] for t in trade_log]
    peak   = equity[0]
    max_dd = 0.0
    for val in equity:
        peak  = max(peak, val)
        max_dd = max(max_dd, (peak - val) / peak)

    # Sharpe на дневных доходностях
    dates_range   = pd.date_range(
        start=min(t["date"] for t in trade_log),
        end=max(t["date"] for t in trade_log),
        freq="B"
    )
    daily_capital = (
        pd.Series({t["date"]: t["capital"] for t in trade_log})
        .reindex(dates_range).ffill().bfill()
    )
    daily_returns = daily_capital.pct_change().dropna()
    sharpe = (
        (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        if len(daily_returns) >= 2 and daily_returns.std() > 0 else 0.0
    )

    return {
        **params,
        "total_return":  round(total_return, 2),
        "win_rate":      round(win_rate, 1),
        "profit_factor": round(pf, 2),
        "max_drawdown":  round(max_dd * 100, 2),
        "sharpe_ratio":  round(sharpe, 3),
        "num_trades":    len(trade_log),
        "final_capital": round(capital, 2),
    }


# ══════════════════════════════════════════════════════════════════════
#  GRID SEARCH
# ══════════════════════════════════════════════════════════════════════

def grid_search(all_data: dict, spy_data: pd.DataFrame) -> pd.DataFrame:
    combos = list(itertools.product(*PARAM_GRID.values()))
    keys   = list(PARAM_GRID.keys())
    total  = len(combos)
    print(f"\n🔍 Grid Search: {total} комбинаций\n")

    results = []
    for idx, combo in enumerate(combos, 1):
        result = run_backtest(all_data, spy_data, dict(zip(keys, combo)))
        if result:
            results.append(result)
        if idx % 10 == 0 or idx == total:
            best = max((r["sharpe_ratio"] for r in results), default=0)
            print(f"  [{idx}/{total}] лучший Sharpe: {best:.3f}")

    df = pd.DataFrame(results).sort_values("sharpe_ratio", ascending=False)
    return df.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════
#  WALK-FORWARD
# ══════════════════════════════════════════════════════════════════════

def _slice(all_data, spy_data, date_from, date_to):
    sliced = {
        s: df.loc[(df.index >= date_from) & (df.index < date_to)]
        for s, df in all_data.items()
    }
    spy_sl = spy_data.loc[(spy_data.index >= date_from) & (spy_data.index < date_to)]
    return sliced, spy_sl


def _best_params(all_data, spy_data) -> dict | None:
    keys   = list(PARAM_GRID.keys())
    combos = list(itertools.product(*PARAM_GRID.values()))
    best_r = best_p = None
    for combo in combos:
        p = dict(zip(keys, combo))
        r = run_backtest(all_data, spy_data, p)
        if r and (best_r is None or r["sharpe_ratio"] > best_r["sharpe_ratio"]):
            best_r, best_p = r, p
    return best_p


def walk_forward(all_data: dict, spy_data: pd.DataFrame) -> pd.DataFrame:
    start  = spy_data.index.min()
    end    = spy_data.index.max()
    cursor = start
    rows   = []
    fold   = 1

    while True:
        train_end = cursor  + pd.DateOffset(months=WF_TRAIN_MONTHS)
        test_end  = train_end + pd.DateOffset(months=WF_TEST_MONTHS)
        if test_end > end:
            break

        print(f"\n  📅 Fold {fold}:")
        print(f"     Train: {cursor.date()} → {train_end.date()}")
        print(f"     Test : {train_end.date()} → {test_end.date()}")

        train_d, train_s = _slice(all_data, spy_data, cursor, train_end)
        best_p = _best_params(train_d, train_s)
        if not best_p:
            cursor += pd.DateOffset(months=WF_TEST_MONTHS)
            fold   += 1
            continue

        test_d, test_s = _slice(all_data, spy_data, train_end, test_end)
        result = run_backtest(test_d, test_s, best_p)
        if not result:
            cursor += pd.DateOffset(months=WF_TEST_MONTHS)
            fold   += 1
            continue

        rows.append({
            "fold":              fold,
            "train_start":       cursor.date(),
            "train_end":         train_end.date(),
            "test_start":        train_end.date(),
            "test_end":          test_end.date(),
            "total_return":      result["total_return"],
            "sharpe_ratio":      result["sharpe_ratio"],
            "win_rate":          result["win_rate"],
            "profit_factor":     result["profit_factor"],
            "max_drawdown":      result["max_drawdown"],
            "num_trades":        result["num_trades"],
            **{k: best_p[k] for k in PARAM_GRID},
        })
        print(f"     ✅ Return: {result['total_return']:+.2f}%  "
              f"Sharpe: {result['sharpe_ratio']:.3f}  "
              f"WinRate: {result['win_rate']:.1f}%")

        cursor += pd.DateOffset(months=WF_TEST_MONTHS)
        fold   += 1

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════
#  ГРАФИКИ
# ══════════════════════════════════════════════════════════════════════

def plot_grid_search(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Grid Search", fontsize=13, fontweight="bold")

    axes[0].hist(df["sharpe_ratio"], bins=20, color="#9C27B0", edgecolor="white")
    axes[0].axvline(0, color="red", linestyle="--", linewidth=1)
    axes[0].axvline(1, color="green", linestyle="--", linewidth=1)
    axes[0].set_title("Sharpe Ratio")
    axes[0].grid(alpha=0.3)

    axes[1].hist(df["total_return"], bins=20, color="#2196F3", edgecolor="white")
    axes[1].axvline(0, color="red", linestyle="--", linewidth=1)
    axes[1].set_title("Total Return (%)")
    axes[1].grid(alpha=0.3)

    sc = axes[2].scatter(df["total_return"], df["sharpe_ratio"],
                         c=df["max_drawdown"], cmap="RdYlGn_r",
                         alpha=0.7, s=40)
    axes[2].axvline(0, color="gray", linestyle="--", linewidth=0.8)
    axes[2].axhline(0, color="gray", linestyle="--", linewidth=0.8)
    axes[2].set_title("Return vs Sharpe\n(цвет = Max Drawdown)")
    plt.colorbar(sc, ax=axes[2], label="Max DD (%)")

    plt.tight_layout()
    plt.savefig("grid_search_chart.png", dpi=150)
    plt.show()
    print("📊 grid_search_chart.png")


def plot_walk_forward(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("Walk-Forward Test", fontsize=13, fontweight="bold")
    folds  = df["fold"].tolist()
    colors = ["#4CAF50" if r > 0 else "#F44336" for r in df["total_return"]]

    axes[0, 0].bar(folds, df["total_return"], color=colors, edgecolor="white")
    axes[0, 0].axhline(0, color="black", linewidth=0.8)
    axes[0, 0].set_title("Total Return по фолдам (%)")
    axes[0, 0].grid(alpha=0.3)

    cumulative = (1 + df["total_return"] / 100).cumprod() * INITIAL_CAPITAL
    axes[0, 1].plot(folds, cumulative, color="#2196F3", linewidth=2, marker="o")
    axes[0, 1].axhline(INITIAL_CAPITAL, color="gray", linestyle="--", linewidth=0.8)
    axes[0, 1].set_title("Накопленный капитал ($)")
    axes[0, 1].grid(alpha=0.3)

    axes[1, 0].bar(folds, df["win_rate"], color="#FF9800", edgecolor="white")
    axes[1, 0].axhline(50, color="red", linestyle="--", linewidth=0.8)
    axes[1, 0].set_title("Win Rate по фолдам (%)")
    axes[1, 0].set_ylim(0, 100)
    axes[1, 0].grid(alpha=0.3)

    axes[1, 1].bar(folds, df["max_drawdown"], color="#9C27B0", edgecolor="white")
    axes[1, 1].set_title("Max Drawdown по фолдам (%)")
    axes[1, 1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig("walk_forward_chart.png", dpi=150)
    plt.show()
    print("📊 walk_forward_chart.png")


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("📥 Загружаем данные...")
    spy_data = prepare_data("SPY", period="5y")
    all_data = {}
    for sym in SYMBOLS:
        print(f"  {sym}...")
        d = prepare_data(sym, period="5y")
        if d is not None:
            all_data[sym] = d

    # ── Grid Search ───────────────────────────────────────────────────
    gs_df = grid_search(all_data, spy_data)

    print("\n" + "═" * 70)
    print("🏆 ТОП-10 КОМБИНАЦИЙ")
    print("═" * 70)
    cols = ["risk_per_trade", "trailing_atr_mult", "volume_filter_mult",
            "max_positions", "rsi_low", "rsi_high",
            "total_return", "win_rate", "sharpe_ratio",
            "profit_factor", "max_drawdown", "num_trades"]
    print(gs_df[cols].head(10).to_string(index=True))

    best = gs_df.iloc[0]
    print(f"\n✅ ЛУЧШАЯ КОМБИНАЦИЯ:")
    print(f"   risk_per_trade     = {best['risk_per_trade']}")
    print(f"   trailing_atr_mult  = {best['trailing_atr_mult']}")
    print(f"   volume_filter_mult = {best['volume_filter_mult']}")
    print(f"   max_positions      = {int(best['max_positions'])}")
    print(f"   rsi_low / rsi_high = {int(best['rsi_low'])} / {int(best['rsi_high'])}")
    print(f"\n   📈 Доходность   : {best['total_return']:+.2f}%")
    print(f"   📐 Sharpe Ratio : {best['sharpe_ratio']:.3f}")
    print(f"   🎯 Win Rate     : {best['win_rate']:.1f}%")
    print(f"   ⚖️  Profit Factor: {best['profit_factor']:.2f}")
    print(f"   📉 Max Drawdown : {best['max_drawdown']:.2f}%")
    print(f"   🔢 Сделок       : {int(best['num_trades'])}")

    gs_df.to_csv("grid_search_results.csv", index=False)
    print("\n💾 grid_search_results.csv")
    plot_grid_search(gs_df)

    # ── Walk-Forward ──────────────────────────────────────────────────
    print("\n" + "═" * 70)
    print(f"🚶 WALK-FORWARD  (train={WF_TRAIN_MONTHS}м / test={WF_TEST_MONTHS}м)")
    print("═" * 70)

    wf_df = walk_forward(all_data, spy_data)

    if wf_df.empty:
        print("⚠️  Нет результатов walk-forward")
    else:
        wf_cols = ["fold", "test_start", "test_end",
                   "total_return", "sharpe_ratio", "win_rate",
                   "profit_factor", "max_drawdown", "num_trades"]
        print("\n" + wf_df[wf_cols].to_string(index=False))
        print(f"\n  Фолдов всего      : {len(wf_df)}")
        print(f"  Прибыльных        : {(wf_df['total_return']>0).sum()} "
              f"({(wf_df['total_return']>0).mean()*100:.0f}%)")
        print(f"  Avg доходность    : {wf_df['total_return'].mean():+.2f}%")
        print(f"  Avg Sharpe        : {wf_df['sharpe_ratio'].mean():.3f}")
        print(f"  Avg Win Rate      : {wf_df['win_rate'].mean():.1f}%")
        print(f"  Avg Max Drawdown  : {wf_df['max_drawdown'].mean():.2f}%")

        wf_df.to_csv("walk_forward_results.csv", index=False)
        print("\n💾 walk_forward_results.csv")
        plot_walk_forward(wf_df)
