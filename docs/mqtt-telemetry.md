# MQTT for reactor telemetry

MQTT is a pub/sub protocol built for sensor streams. It fits this plant thematically. It is only worth adding if more than one consumer cares about the same topics.

## Current path (no broker)

```
incident reports → compute_metrics → FastAPI /ws/telemetry → Vue useReactorTelemetry
```

The API computes a metric blob every 1s and pushes it over one WebSocket. The Vue dashboard is the only live consumer. That is request/response-shaped pub/sub: one socket, one JSON object, one UI.

`compute_metrics` stays the source of truth either way. MQTT would change how those numbers leave the process, not how they are calculated.

## When it is not worth it

If the only consumer stays one Vue dashboard, MQTT is extra moving parts for the same 1Hz JSON. Browsers cannot speak raw MQTT TCP — the client would need MQTT.js over WebSockets to a broker (Mosquitto/EMQX, typically `:9001`). Auth is a second story (broker username/ACL), separate from FastAPI JWT.

Keep `/ws/telemetry` until a second consumer exists. Then the broker earns its keep: many publishers, many subscribers, no new WS endpoint per listener.

## Suggested shape if we add it

Do not rip out the WebSocket. Publish the same metrics and let consumers opt in:

```
incident reports → compute_metrics → MQTT broker → Vue (mqtt.js)
                                      ├─ other consumers below
                                      └─ existing /ws/telemetry (keep)
```

Topic sketch (one blob first, split later):

```
snrub/reactor/metrics                  # full dict (compat with current WS payload)
snrub/reactor/core/power
snrub/reactor/core/temperature
snrub/reactor/core/reactivity
snrub/reactor/coolant/flow
snrub/reactor/coolant/pressure
snrub/reactor/radiation/level
snrub/reactor/containment/integrity
snrub/alarms/{metric}                  # threshold crossings only
snrub/reactor/control/#                # commands (SCRAM, rods) — later
```

A later, more plant-like step: split publishers so coolant / radiation / core are separate processes, and the API becomes a subscriber that aggregates.

---

## Other consumers (why a broker is worth it)

Each of these can subscribe without a new FastAPI route. That is the answer to "one dashboard is not enough."

### 1. Alarm / annunciator panel

A second UI (or a strip on the existing dashboard) that only cares about warning/danger crossings, not the full time series.

- Subscribe: `snrub/alarms/#` (or the metric topics, locally thresholded)
- Uses the bands already defined in `app/services/telemetry.md` (e.g. core temp warning 900–1000°C, danger >1000°C)
- Classic control-room tile wall: lit tile per trip, silence/ack as a publish back onto `snrub/alarms/{id}/ack`

This is the smallest second consumer and the one that most justifies topic-per-metric.

### 2. Incident auto-reporter

Closes the loop the system already has: incidents move metrics; metrics should be able to spawn incidents.

- Subscribe: metric or alarm topics
- On sustained danger (e.g. `coolant_flow_rate` < 50% for N seconds), POST an `IncidentReport` (`coolant_flow_reduction`, status `REPORTED`)
- Fits existing models (`incident_reports`, `incident_types`) and `STATUS_WEIGHT` in `telemetry.py`
- Makes drift/lerp in `compute_metrics` visible: a trip is not a one-frame spike

Keep a debounce / "already open" check so it does not flood the table.

### 3. Email / pager (Mailhog)

The stack already has FastAPI-Mail and Mailhog. A notifier is a natural subscriber.

- Subscribe: `snrub/alarms/#`
- On danger, send "core temperature 1040°C" to on-shift operators (or Mailhog in dev)
- Role-aware later: `ADMIN` / `SUPER_ADMIN` vs `VIEWER` get different lists
- Same pattern as `app/services/email.py`, but event-driven instead of request-driven

This is the first consumer that is not a browser.

### 4. Historian (time-series log)

The current WS is fire-and-forget. Nothing keeps the 1Hz series after the chart buffer (50 points in Vue) rolls off.

- Subscribe: `snrub/reactor/#`
- Append readings to Postgres, a file, or a TSDB
- Powers "what did coolant pressure do in the hour before the report?"
- Retained messages give last-known value on subscribe; the historian gives the past

Nuclear-flavoured name: plant historian / sequence-of-events log.

### 5. Audit / compliance writer

Same idea as the historian, but event-shaped rather than sample-shaped.

- Subscribe: alarms, acks, control commands, incident status changes
- Write an append-only audit trail (who silenced what, when SCRAM was requested)
- Maps to the existing user/role model if the publisher includes `uid` / role

Useful even if the historian is skipped: alarms matter more than every temperature tick.

### 6. Shift kiosk / wall display

A read-only client (second Vue route, or the React compose profile) with no operator controls.

- Subscribe: metrics + alarms
- No need to duplicate `/ws/telemetry` auth/query-token handling if the kiosk uses a broker ACL
- `VIEWER` analogue: see the plant, cannot command it

Both `snrub.client` and `snrub.react` can subscribe to the same topics. That is harder to do cleanly with one FastAPI WebSocket that is wired to one composable.

### 7. Interlock / SCRAM simulator

A non-UI process that watches for trip conditions and publishes control actions.

- Subscribe: `core/temperature`, `core/reactivity`, `coolant/flow`
- If reactivity > +3 and temp > 1000°C, publish `snrub/reactor/control/scram`
- A second subscriber (or the API) applies the effect: drive power/reactivity toward shutdown, maybe open a `emergency_shutdown` style incident
- Fits phase-2 metrics in `telemetry.md`: backup power, ECCS availability, alarm-system health

This is where MQTT is not just "charts over a different pipe" — it is a bus between simulated plant systems.

### 8. Operator alertness / human-factor service

`telemetry.md` already defines Operator Alertness Index and incident types `operator_asleep_at_station` / `operator_intoxicated_at_station`.

- Subscribe: operator activity (dashboard focus, ack rate, time since last action)
- Publish: `snrub/crew/alertness` (0–100)
- Downstream: fatigue meter on the UI, or auto-report if the index stays below 50

Keeps the "human factor" twist on the same bus as the physics metrics.

### 9. Sound / PA simulator

- Subscribe: `snrub/alarms/#`
- Play a klaxon (or log `KLAXON: radiation 80 mSv/h`) when radiation > 50 or containment < 85%
- Trivial consumer; good first "hello MQTT" script (`mosquitto_sub` + a local beep)

### 10. Training / replay publisher

Not only a consumer: a publisher that replays a recorded incident onto the live topics.

- Historian (or a fixture file) republishes a past sequence at 1Hz
- Dashboard, alarms, email notifier, and SCRAM interlock all react as if live
- Useful for demos and for testing `STATUS_WEIGHT` / impact-map changes without seeding new reports

### 11. Ops CLI

Same role as `docker compose exec db psql` today.

```bash
mosquitto_sub -h localhost -t 'snrub/#' -v
```

Live topic dump while filing an incident in the UI. No extra API, no Vue rebuild.

---

## What to build first

Smallest slice that makes MQTT more than a second WebSocket:

1. Mosquitto in `docker-compose` (MQTT + WS listener)
2. API publishes the existing `compute_metrics` dict to `snrub/reactor/metrics`
3. One non-UI consumer: either the Mailhog alarm notifier or a historian writer
4. Vue can keep `/ws/telemetry` until (3) is useful; then optionally subscribe with MQTT.js

Topic-per-metric, fake sensor processes, and the SCRAM interlock come after the broker has at least two real subscribers.
