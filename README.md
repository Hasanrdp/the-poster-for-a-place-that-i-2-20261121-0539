# SELKARA — A Travel Poster for a Place That Isn't There

[![make.fun](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Hasanrdp/the-poster-for-a-place-that-i-2-20261121-0539/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Hasanrdp/the-poster-for-a-place-that-i-2-20261121-0539/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)

A travel poster for Selkara, an island that is not on any map, built for the
[the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
bounty on make.fun.

## The place

Selkara is an island where the sea holds the sunset. Golden hour never quite
ends there: a ringed planet hangs in the dusk sky, a low sun melts into a
mirror sea, and a red-banded lighthouse on the headland throws its beam
across the water toward a lone sail. The poster's promise is one evening on
that headland — warm light, still water, and a sky no earthly coast has.

## The poster

- **The name, set with intent** — SELKARA in large cream capitals across
  the top of the picture, with a thin gold rule and a diamond beneath it,
  so the eye moves from the name to the landmark and down to the horizon.
- **One landmark** — the lighthouse and its beam, with a small white town
  along the cliff top and two cypresses on the edge.
- **A place that does not exist** — the ringed planet in the dusk sky is the
  giveaway: no real destination looks like this.
- **Colour with a job to do** — indigo dusk melting into amber at the
  horizon, a deep teal sea, and a gold glitter-path on the water leading the
  eye from the sun to the sail.

## How it is made

`main.py` is a single-file Python 3 program using only the standard library.
It draws the whole poster with a hand-built 5x7 bitmap font and a hand-written
PNG encoder, and writes a 1024x1024 PNG. No network, no clock, no randomness:
two runs produce byte-identical output.

Run it locally:

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```
