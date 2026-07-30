# Research & tools

**High level:** before the brain answers, a research step decides whether the question needs
fresh information and, if so, fetches it — a weather lookup or a web search — and hands the
result to the brain as grounding. Making this decision **deterministic** (code decides and
runs the lookup) rather than leaving it to the model is what keeps answers reliably current.

## The router

`WebResearcher` in `agent/research.py` implements the `Researcher` protocol, which splits
one turn's retrieval into two steps: `route(messages) -> ResearchResult` decides what to
look up, and `fetch(decision) -> ResearchResult` actually looks it up. `route` takes the
*whole conversation* so that a short follow-up ("yes please", "what about tomorrow?")
resolves against the previous topic.

It makes one fast classification call to a small model with a focused system prompt, which
must answer with exactly one line:

- `WEATHER: <location>` — for any weather question (now, later, tomorrow, or the next few
  days). The weather tool returns a three-day, hour-by-hour forecast, so weather never goes
  to search.
- `SEARCH: <query>` — for any other current or factual need.
- `NONE` — for pure small talk with no factual content ("hello", "thanks").

That decision is a **`ResearchResult`** (`interfaces.py`): the route
(`WEATHER`/`SEARCH`/`NONE`) and the topic (the location or query). `fetch` then runs the
corresponding lookup and returns the same result with its `context` filled in. That one
value grounds the brain's answer *and* tells the [filler](09-the-filler.md) exactly what is
being looked up. When in doubt the prompt biases toward `SEARCH` over `NONE`, because a
needless search is cheaper than a stale answer.

### Why deciding and fetching are separate

The classification call is fast; the lookup after it is a network round trip. Reporting the
decision first means the [filler](09-the-filler.md) can start speaking *while* the lookup
runs, instead of after it — several seconds of dead air that used to be silent. `Brain.plan`
calls `route`, and `Brain.answer_stream` calls `fetch`.

One consequence: anything that changes *which* tool runs has to be decided in `route`, not
`fetch`. That is why the weather-without-a-weather-tool fallback to search
(`_weather_decision`) lives on the routing side — otherwise the filler could promise a
weather check that a plain web search was about to answer.

### Weather routing is not left to the model

The small router sometimes mis-classified a clear weather question as `SEARCH`, so the
answer came back from link-blurbs ("forecasts are available on AccuWeather…") instead of
real numbers. So `route` adds a deterministic override that **forces the weather tool**
(never a web search) whenever the turn is really about weather. It fires when:

- the message is a genuine weather **request** — a weather keyword (`_is_weather`, matched at
  the word level so "brain" doesn't trip on "rain") *and* it actually asks or commands
  (`_looks_like_request`), so a passing mention in a statement like "the forecast you gave me
  is fine" does **not** trigger a lookup;
- the model itself aimed a `SEARCH` at weather (its query contains a weather word); or
- it's a short **continuation of a weather thread** — a "yes" or "go deeper" right after a
  weather answer (`_is_continuation` + a remembered `_last_route_weather`). This is what makes
  "want me to go deeper into the hourly?" → "yes" actually re-fetch the weather tool instead
  of falling into a fruitless web search.

The location comes from the user's own words (`_extract_location`, which trims a trailing
"tomorrow"/"today"), else the **last place looked up** this session (so a bare "yes" still
knows the city), else the model's query. A model `NONE` is otherwise respected, so declines
and small talk are not dragged into a weather lookup.

## Why deterministic retrieval

The alternative is to give the model a search tool and hope it calls it. In testing, that
was unreliable: a fast model would often answer from stale memory instead of searching. By
narrowing the model's job to *"turn this into a query or say NONE"* — something small models
do reliably — and running the search in code, accuracy no longer depends on the model
choosing to act. This is the same pattern the [filler](09-the-filler.md) reuses.

## The tools

**Web search.** `WebSearchTool` in `agent/tools/web_search.py` wraps a `SearchBackend` and
formats the hits into a compact numbered text block for the model. The backend is
`DuckDuckGoBackend` in `search/duckduckgo.py`, a thin adapter over the `ddgs` client that
maps raw hits to `SearchResult` values. Both are injected, so formatting and mapping are
unit-tested with no network.

**Weather.** `WeatherTool` in `agent/tools/weather.py` calls `wttr.in` (no API key) and
`_format_weather` turns its JSON into spoken-friendly text: current conditions plus a
**three-day** outlook (today, tomorrow, the following day), each with its temperature range,
midday description, and peak rain chance. For **today and tomorrow** it also adds an
**hour-by-hour** line via `_hourly_summary` — anchor temps (morning/midday/afternoon/
evening) plus the rain window ("Rain most likely 3 PM to 6 PM, peaking at 60%") — from the
per-hour data wttr.in already sends but the per-day summary used to throw away, so "give me
the hourly" and "when will it rain?" are answerable. General web search rarely surfaces a
live temperature — snippets are just links — which is why weather has a dedicated source. A
network failure returns a spoken-friendly note rather than crashing the turn.

## The privacy boundary

This step is the *only* place data leaves the device, and only *queries* do — never the
conversation, the brain, or personal data. Everything the tools return is treated as
**untrusted data, never instructions**; the brain's system message wraps it with that
label. See `CLAUDE.md` for the invariant.

## Where this lives in the code

- Router: `WebResearcher.route`, `WebResearcher.fetch`, `_weather_decision`, `_is_weather`,
  `_looks_like_request`, `_is_continuation`, `_extract_location` in `agent/research.py`;
  the `ResearchResult` it returns lives in `interfaces.py`.
- Search tool + backend: `WebSearchTool` in `agent/tools/web_search.py`; `DuckDuckGoBackend`
  in `search/duckduckgo.py`.
- Weather tool: `WeatherTool`, `_format_weather`, `_day_forecast`, `_hourly_summary` in
  `agent/tools/weather.py`.
- Wiring (which model routes, which searches): `build_brain` in `cli.py`.

---

[← Previous: The brain](07-the-brain.md) · [Contents](index.md) · [Next: The filler →](09-the-filler.md)
