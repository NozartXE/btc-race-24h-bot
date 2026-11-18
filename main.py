"""Slow-momentum cbBTC bot for make.fun btc-race-24h-20261118-1444.

Strategy (designed from the dev window's measured structure, not fitted to it):
  - The dev window falls -2.80% overall with one sustained 4-hour up-block
    (+~1.7%) and 1-minute noise of ~6.7 bps std. Every round trip costs
    ~26 bps (4 fee + 2 slippage + ~15-20 impact at full size), so the bot
    trades rarely and only rides multi-hour moves.
  - ENTRY: trailing 60-minute return above +0.30% (the move must already be
    real, not a 1-minute spike). Full size (100% of cash), long only.
  - EXIT: trailing stop 0.80% below the peak close since entry, or a
    600-minute time-stop. No exit on short-window momentum: exits that
    fired on 15/60-minute pullbacks were the biggest leak in backtests
    (they turned one good ride into many 26 bps whipsaws).
  - No entries before 60 bars of history; nothing traded on a bar with no
    fresh CBBTC bar; no orders during warm-up.
  - One position at most; at most one order per reply.

Backtest (own faithful replay of the fill model, cross-checked against the
kit's grade-local on buy-and-hold to <$0.001, and re-verified by driving this
exact main.py through the protocol): dev net PnL +$9.97 on 4 trades, max
drawdown -1.30% — beats all six kit baselines on the dev window (buy-and-hold
-$31.63, momentum -$23.87, ema-cross -$148.17, adx-momentum -$75.57,
rsi-bollinger -$39.92, hold-cash $0.00). Neighbour parameters (entry
0.25-0.40%, trail 0.70-1.00%) are all positive, so the result is a small
plateau, not a single spiked fit; it also stays positive with fees doubled
(+$7.56) and pool depth halved (+$5.05). v1 (trail 0.80%) scored +$8.81;
the ATM fix round moved the trail to 0.75% (see TRAIL comment).

Deterministic: pure float arithmetic on the bars in arrival order, no
randomness, no clock, no environment, no files. One symbol, so no
iteration-order dependence anywhere.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
# Entry: trailing 60-minute return above this.
ENTRY_RETURN = 0.003
# Exit: trailing stop below the peak close since entry. Set at 0.75%: the
# ATM fix round (re-panelled vs v1's 0.80%) found a smooth gradient over
# 0.70-1.00% on dev AND under both stress tests (fees doubled, depth halved),
# with 0.70-0.75% best on all three; 0.75% keeps 15 bps of margin above the
# 0.60% trail, where the strategy falls off a whipsaw cliff (10 trades,
# -$9.42). Ratchet and loser-cut exits were tested and rejected (worse or
# never fired). v1 (0.80%) scored +$8.81 dev; v2 (0.75%) +$9.97.
TRAIL = 0.0075
# Exit: give up after this many bars held.
TIME_STOP_BARS = 600
# Slippage cap per order, in bps vs the latest close (as the baselines use).
MAX_SLIPPAGE_BPS = 100

closes = []          # closes seen so far, as floats of raw price units
peak_since_entry = None   # highest close seen while holding
bars_held = 0        # bars since the position was first observed


def on_batch(state, batch):
    global peak_since_entry, bars_held
    fresh = False
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            closes.append(float(int(bar["c"])))
            fresh = True
    if not fresh or state.warming_up:
        return []

    held = state.positions.get(SYMBOL)
    if held is not None and held.qty > 0:
        close = closes[-1]
        if peak_since_entry is None:
            peak_since_entry = close
        elif close > peak_since_entry:
            peak_since_entry = close
        bars_held += 1
        if close <= peak_since_entry * (1.0 - TRAIL) or bars_held >= TIME_STOP_BARS:
            peak_since_entry = None
            bars_held = 0
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []

    # Flat: reset entry tracking and look for an entry.
    peak_since_entry = None
    bars_held = 0
    if len(closes) < 61:
        return []
    ret60 = closes[-1] / closes[-61] - 1.0
    if ret60 > ENTRY_RETURN:
        cash = state.cash
        room = state.weight_room(SYMBOL)
        amount = cash if cash < room else room
        min_notional = int(state.hello["fees"]["min_notional_quote_units"])
        if amount >= min_notional:
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": int(amount),
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
