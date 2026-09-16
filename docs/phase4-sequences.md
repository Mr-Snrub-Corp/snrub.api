# Phase 4 sequences (as-built)

How the plant actually runs after Phase 4 of [roadmap.md](roadmap.md).
Six small sequences, not one end-to-end sketch: REST publishes a setpoint; a
**separate simulator process** integrates it on the next 1Hz tick; incidents
are a side effect of true state, not the driver.

Client is an actor only (God-mode REST, `/ws/telemetry`, mqtt.js alarm panel).
Phase 5 SCRAM and Phase 6 sensor fusion are not here.

Code: `app/simulator.py`, `app/controllers/actuators.py`,
`app/services/plant_model.py`, `app/services/sensors.py`,
`app/services/incident_emitter.py`, `app/controllers/telemetry.py`,
`emqx/acl.conf`.

## Context

```mermaid
flowchart LR
  GodMode["God-mode REST"] --> EMQX
  EMQX --> Sim["Simulator 1Hz"]
  Sim --> DB["plant_states"]
  Sim --> Inc["incident_reports"]
  Sim --> EMQX
  Dash["Dashboard WS"] --> API["FastAPI"]
  API --> DB
  Alarms["Alarm panel mqtt.js"] --> EMQX
```

| Fact | Detail |
|---|---|
| Topic prefix | First path segment is `MQTT_BASE_TOPIC` (default `snrub`). It is a **broker namespace**, not a service and not the API — it keeps this plant's topics off someone else's tree on a shared broker. Diagrams write `{base}/…`. Could be any string. |
| MQTT usernames | `snrub_api` / `snrub_sim` are **broker login names** (who may publish/subscribe). Same project word, different thing from the topic prefix. |
| ACL | Only username `snrub_api` may **publish** `{base}/plant/actuators/#`; only `snrub_sim` may **subscribe**. Browsers are anonymous on WS `:8083` and are denied that tree (`emqx/acl.conf`). |
| Two publishers | API `lifespan` in `app/main.py` (actuator publishes) and the simulator (telemetry + actuator subscribe). Both wrap `MqttPublisher`. |
| QoS / retain | QoS 0 everywhere. Retain only on actuator setpoints and alarm level messages. See [QoS and persistence.md](QoS%20and%20persistence.md). |
| GET actuators | `GET /api/godmode/actuators` returns **nominals** (`ACTUATOR_NOMINAL`), not live setpoints. The API is stateless. |
| Pink bands | MQTT topics. Semi-transparent pink (`rgba(236, 72, 153, 0.28)`) so the wash reads on light and dark; message text stays theme colour. |

---

## 1. Set an actuator

*How does a lever reach the bus?*

Does not continue into the tick. JWT stays in charge; the browser never holds
broker creds for control.

```mermaid
sequenceDiagram
    actor SA as super_admin
    participant UI as God-mode view
    participant Route as PUT /api/godmode/actuators
    participant Auth as verify_super_admin_access
    participant Dep as get_mqtt_publisher
    participant Ctrl as set_actuator
    participant B as EMQX

    SA->>UI: drag lever 0-100
    UI->>Route: PUT /api/godmode/actuators/{actuator} JWT body value
    Route->>Auth: Depends
    alt not super_admin
        Auth-->>UI: 403
    else JWT ok
        Route->>Dep: Depends
        alt broker down
            Dep-->>UI: 503 MQTT broker unavailable
        else connected
            Route->>Ctrl: actuator request user_id publisher
            rect rgba(236, 72, 153, 0.28)
                Ctrl->>B: retained {base}/plant/actuators/{name}
            end
            Note over B: payload actuator value kind set_by ts
            Ctrl-->>UI: 200 actuator value kind
        end
    end
```

`kind` is stamped server-side (`command` for rod/pump/steam, `fault` for
leak/xenon). The client sends only `value`.

---

## 2. Simulator consumes setpoints

*How does the plant hear it?*

A background task, not the tick. `actuator_state` is in-process memory;
missing keys stay at `ACTUATOR_NOMINAL`. Retained messages hydrate on
subscribe, so a simulator restart picks up last setpoints from the broker.

`{base}` is `MQTT_BASE_TOPIC` (default `snrub`) — a namespace string, not a
process. The meaningful path is `plant/actuators/#`.

```mermaid
sequenceDiagram
    participant B as EMQX
    participant Sim as run_simulator
    participant Sub as _consume_actuators
    participant Apply as _apply_actuator_message
    participant Mem as actuator_state

    Sim->>Mem: seed ACTUATOR_NOMINAL
    rect rgba(236, 72, 153, 0.28)
        Sim->>B: subscribe {base}/plant/actuators/#
    end
    Sim->>Sub: spawn background task
    B-->>Sub: retained then live messages
    Sub->>Apply: payload bytes
    alt malformed or unknown actuator
        Apply->>Apply: log and ignore
    else known
        Apply->>Mem: clamp 0-100 store value
    end
```

---

## 3. One tick

*What happens every second?*

This is the invert: actuators drive true state; sensors sample it; incidents
are emitted from **true** state after the snapshot is saved.

```mermaid
sequenceDiagram
    participant Sim as run_simulator
    participant Adv as _advance_plant
    participant PM as plant_model
    participant SN as sensors
    participant DB as plant_states
    participant EM as incident_emitter

    loop every 1s
        Sim->>Adv: state prev_readings tick actuator_state streaks
        Adv->>PM: targets_from_actuators
        PM-->>Adv: metric targets
        Adv->>PM: step lerp coupling temp-to-reactivity feedback
        PM-->>Adv: new true state
        Adv->>SN: sample_all noise lag
        SN-->>Adv: measured readings
        Adv->>DB: persist true_* and measured_*
        Adv->>EM: emit true state
    end
```

`step()` eases each metric toward coupled targets (`alpha = 1 - exp(-dt / tau)`).
`sample_all()` applies per-sensor gaussian noise and optional lag
(thermowell on core temp, detector integration on radiation).

---

## 4. Telemetry and alarms leave the process

*What do operators see on the bus?*

Alarms classify **measured** readings. Incidents in (3) classify **true**
state. A noisy sensor can alarm without filing an incident, and vice versa.

```mermaid
sequenceDiagram
    participant Sim as _publish_tick
    participant Eval as alarms.evaluate
    participant B as EMQX
    participant Panel as Alarm panel mqtt.js

    rect rgba(236, 72, 153, 0.28)
        Sim->>B: {base}/reactor/metrics blob not retained
        loop each metric
            Sim->>B: {base}/reactor/{group}/{metric}
        end
    end
    Sim->>Eval: measured readings
    Eval-->>Sim: per-metric AlarmLevel
    loop level changed vs last tick
        rect rgba(236, 72, 153, 0.28)
            Sim->>B: retained {base}/alarms/{metric}
        end
        B-->>Panel: tile update
    end
```

Per-metric paths (`METRIC_TOPIC_PATHS`): `core/power`, `core/temperature`,
`core/reactivity`, `coolant/flow`, `coolant/pressure`, `radiation/level`,
`containment/integrity`. Alarm payload: `{metric, level, value, ts}`.

Panels may publish `{base}/alarms/{metric}/ack` (ACL allows it). Ack is a
panel-side silence, not a plant command.

---

## 5. Dashboard WebSocket

*Why does `/ws/telemetry` still exist?*

Compat path. The API does not compute the plant; it reads the latest
simulator snapshot. MQTT consumers can skip this socket.

```mermaid
sequenceDiagram
    actor Op as operator
    participant D as Dashboard
    participant WS as /ws/telemetry
    participant Auth as authenticate_websocket
    participant Ctrl as get_reactor_metrics
    participant DB as plant_states

    Op->>D: open dashboard
    D->>WS: connect token query param
    WS->>Auth: decode JWT user exists
    alt bad token or missing user
        Auth-->>D: close 4401
    else ok
        WS-->>D: accepted
        loop every 1s
            WS->>Ctrl: session
            Ctrl->>DB: latest plant_states row
            alt no snapshot yet
                Ctrl-->>WS: BASE_METRICS
            else row exists
                Ctrl-->>WS: measured_* dict
            end
            WS-->>D: metrics JSON
        end
    end
```

---

## 6. Auto-incident

*When does a lever become a row in `incident_reports`?*

WARNING stays alarm-only. DANGER on **true** state must hold for
`DEBOUNCE_TICKS` (3) consecutive ticks. An open `[auto]` report for that
code blocks a second file.

Example: `leak_rate` 100 → coolant flow target drops → after a few ticks
true `coolant_flow_rate` is DANGER-low → `coolant_flow_reduction`.

```mermaid
sequenceDiagram
    participant Adv as _advance_plant
    participant EM as incident_emitter.emit
    participant Class as current_excursions
    participant Streak as update_streaks
    participant File as file_auto_reports
    participant DB as incident_reports

    Adv->>EM: true state streaks session
    EM->>Class: classify vs SETPOINTS
    Class-->>EM: metric to incident_type_code for DANGER only
    EM->>Streak: count consecutive DANGER ticks
    alt streak under 3
        Streak-->>EM: not ready
    else streak at least 3
        Streak-->>EM: ready codes
        EM->>File: codes
        alt open auto report already exists
            File->>File: skip
        else none open
            File->>DB: create_report system user description [auto] code
        end
    end
```

`EXCURSION_CODE_MAP` (metric + danger direction → type code):

| Metric | Direction | Code |
|---|---|---|
| `reactor_power` | high | `unrequested_fission_surplus` |
| `core_temperature` | high | `coolant_temperature_exceedance` |
| `reactivity` | high | `reactivity_excursion_risk` |
| `reactivity` | low | `xenon_poisoning_instability` |
| `coolant_flow_rate` | low | `coolant_flow_reduction` |
| `coolant_pressure` | high or low | `steam_pressure_anomaly` |
| `radiation_level` | high | `radiation_level_exceedance` |
| `containment_integrity` | low | `containment_integrity_compromised` |
