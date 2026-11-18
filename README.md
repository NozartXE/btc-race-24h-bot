# btc-race-24h-bot

A cbBTC 1-minute trading bot for the make.fun competition
[`btc-race-24h-20261118-1444`](https://make.fun/bounty/btc-race-24h-20261118-1444)
("Race a BTC trading bot live for 24 hours", $250 pot, 10 paid places).
Paper money only; long only; no shorts, no leverage.

## Strategy: slow momentum, few trades

The dev window falls −2.80% overall with one sustained ~4-hour up-block
(+~1.7%) and 1-minute noise of ~6.7 bps std. A full-size round trip costs
~26 bps (4 fee + 2 slippage + ~15–20 price impact), so the bot trades rarely
and only rides multi-hour moves:

- **Entry:** trailing 60-minute return above +0.30%. Full size (100% of cash).
- **Exit:** trailing stop 0.75% below the peak close since entry, or a
  600-minute time-stop. No exit on short-window momentum — exits that fired
  on 15/60-minute pullbacks were the biggest leak in backtests.
- No entries before 60 bars of history; nothing traded on a bar with no fresh
  CBBTC bar; no orders during warm-up. At most one position, one order per reply.

## Dev-window result (verified)

Driven through the `agent-fun/bars-replay/v1` protocol against the kit's frozen
dev window (1,440 bars), two runs, byte-identical action logs:

| metric | value |
|---|---|
| Net PnL | **+$9.97** (9,970,930 micro-USDC) |
| Trades | 4 |
| Max drawdown | −1.30% |
| Fees paid | $1.62 |
| Determinism | identical action logs, 2/2 runs |

Dev-gate check: net PnL > $0 — **PASS** (with $9.97 of margin).

For comparison, the six kit baselines on the same window (via the kit's
`grade-local`): buy-and-hold −$31.63, momentum −$23.87, ema-cross −$148.17,
adx-momentum −$75.57, rsi-bollinger −$39.92, hold-cash $0.00. This bot beats
all six. Neighbour parameters (entry 0.25–0.40%, trail 0.70–1.00%) are all
positive, and it stays positive with fees doubled (+$7.56) and pool depth
halved (+$5.05) — a small plateau, not a single spiked fit.

Honest caveat: the race window is unseen. The dev edge is two round trips'
worth of trend-riding; a choppy or sharply reversing race window can still
lose money. The design's defence is few trades, a trailing stop, and a
1.30% dev drawdown against a 25% limit.

## Layout

- `main.py` — the bot (Python 3.13, standard library only). Written originally
  for this competition; the strategy was selected from 10 candidate concepts by
  a blind judge panel and then by backtest.
- `vendor/makefun_bars.py` — byte-for-byte copy of the kit's Python SDK shim
  (`sdk/makefun_bars.py`), as the kit explicitly permits.
- `LICENSE` — MIT.

## Run locally

```sh
node <kit>/cli/makefun.mjs grade-local --kit <kit> --bot . --driver docker
```

(The kit's process driver runs Node bots only; a Python bot needs the Docker
driver, or a protocol driver that spawns `python3 -P -s main.py`.)
