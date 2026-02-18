from datetime import datetime, timedelta

from app.models.incident_report import EscalationLevel, IncidentStatus
from app.models.incident_report_subject import SubjectRole


def _days_ago(days, hour=0, minute=0, second=0):
    """Return ISO datetime string for N days ago at the given time."""
    dt = (datetime.now() - timedelta(days=days)).replace(hour=hour, minute=minute, second=second, microsecond=0)
    return dt.isoformat()


INCIDENT_REPORTS = [
    {
        "incident_type_code": "evacuation_required",
        "reported_by_email": "smitty@snrub-corp.io",
        "description": (
            "Unscheduled evacuation initiated in Sector 7G after a control panel fault triggered conflicting"
            " coolant flow readings and a localized alarm. Homer Simpson and Tibor Jankovsky were present at the"
            " station and attempted manual verification, which prolonged response by several minutes. Area cleared"
            " per protocol; follow-up checks found no active hazard. Evacuation lifted after systems reset and"
            " readings stabilized."
        ),
        "severity": 7,
        "status": IncidentStatus.RESOLVED,
        "escalation_level": EscalationLevel.ESCALATED,
        "occurred_at": "2021-09-14T05:16:18",
        "subjects": [
            {"user_email": "h.simpson@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
            {"user_email": "t.jankovsky@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
        ],
    },
    {
        "incident_type_code": "documentation_noncompliance",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "A retrospective compliance audit identified that required operational documentation for a scheduled"
            " safety system verification was incomplete and not filed in accordance with plant record-keeping"
            " procedures. Maintenance and test execution logs were present, but calibration certification and"
            " supervisory sign-off were missing from the permanent record. Review indicates the verification"
            " activity was performed and reactor conditions remained within operational limits; however, the"
            " absence of complete documentation prevented independent validation of procedure adherence and"
            " equipment readiness at the time. The deficiency was classified as a procedural noncompliance"
            " and corrective documentation controls were implemented."
        ),
        "severity": 3,
        "status": IncidentStatus.UNDER_REVIEW,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2021-09-17T10:24:33",
        "subjects": [
            {"user_email": "canary.m.burns@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
        ],
    },
    {
        "incident_type_code": "xenon_poisoning_instability",
        "reported_by_email": "c.charlie@snrub-corp.io",
        "description": (
            "During a routine reactor stability test in Sector 7G, a transient power dip consistent with xenon"
            " poisoning was observed following an unplanned control rod adjustment. Output oscillations remained"
            " within nominal safety margins and self-corrected without intervention.\n\nOperators noted the"
            " anomaly, logged it, and resumed standard procedures. No impact to generation targets. Event"
            " captured for trend analysis and reporting."
        ),
        "severity": 3,
        "status": IncidentStatus.CONTAINED,
        "escalation_level": EscalationLevel.MONITORING,
        "occurred_at": "2022-07-24T10:40:45",
        "subjects": [
            {"user_email": "c.charlie@snrub-corp.io", "role": SubjectRole.WITNESS},
            {"user_email": "l.leonard@snrub-corp.io", "role": SubjectRole.INVOLVED},
        ],
    },
    {
        "incident_type_code": "worker_radiation_exposure",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "Five personnel entered Sector 7G and engaged in unauthorized recreational activity involving live"
            " roosters within a controlled service area. Subsequent monitoring identified minor radiation exposure"
            " consistent with contact with contaminated animals present in the zone. Recorded dose levels remained"
            " within short-duration tolerance limits and no medical intervention was required. The exposure was"
            " determined to result from deliberate disregard of access and conduct protocols. Area decontamination"
            " procedures were completed and the incident was closed following standard reporting."
        ),
        "severity": 4,
        "status": IncidentStatus.CLOSED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2022-10-28T14:07:12",
        "subjects": [
            {"user_email": "b.bernie@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
            {"user_email": "h.simpson@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
            {"user_email": "joe@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
            {"user_email": "angel.of.death@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
            {"user_email": "l.leonard@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
        ],
    },
    {
        "incident_type_code": "industrial_accident",
        "reported_by_email": "c.charlie@snrub-corp.io",
        "description": (
            "During an attempted evacuation following a minor gas leak in Sector 7G, employees Homer, Lenny,"
            " Carl, and Charlie proceeded toward the designated emergency exit. The exit was determined to be a"
            " painted wall feature rather than a functional egress point. No injuries occurred, as the employees"
            " eventually located an alternate route.\nA request was submitted to install a real emergency exit;"
            " management notes the existing wall graphic adequately communicates the concept of evacuation."
            " Incident recorded for reporting purposes only."
        ),
        "severity": 4,
        "status": IncidentStatus.REPORTED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2022-11-11T03:36:12",
        "subjects": [
            {"user_email": "c.charlie@snrub-corp.io", "role": SubjectRole.WITNESS},
            {"user_email": "h.simpson@snrub-corp.io", "role": SubjectRole.WITNESS},
            {"user_email": "l.leonard@snrub-corp.io", "role": SubjectRole.WITNESS},
            {"user_email": "c.carlson@snrub-corp.io", "role": SubjectRole.WITNESS},
        ],
    },
    {
        "incident_type_code": "safety_test_failure",
        "reported_by_email": "c.carlson@snrub-corp.io",
        "description": (
            "A scheduled safety system verification in Sector 7G failed when the emergency core cooling system"
            " did not initiate during a simulated loss-of-coolant scenario. The test sequence was repeated with"
            " identical results.\n\nPreliminary review indicates the system had been left in maintenance bypass"
            " following earlier work and was not restored to operational state. The condition was corrected after"
            " the test, and the system passed on re-verification.\n\nNo real-world hazard occurred; however, the"
            " failure represents a lapse in safety assurance and has been logged for compliance review and trend"
            " reporting."
        ),
        "severity": 2,
        "status": IncidentStatus.CONFIRMED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2023-01-10T04:50:46",
        "subjects": [
            {"user_email": "h.simpson@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
        ],
    },
    {
        "incident_type_code": "contamination_event",
        "reported_by_email": "c.carlson@snrub-corp.io",
        "description": (
            "Trace contamination detected on a work surface in Sector 7G following an informal snack break."
            " Source identified as a mislabeled container that previously held a low-level test sample. Area was"
            " wiped down, items re-labeled, and monitoring confirmed readings returned to background levels. No"
            " exposure recorded."
        ),
        "severity": 3,
        "status": IncidentStatus.MITIGATION_IN_PROGRESS,
        "escalation_level": EscalationLevel.MONITORING,
        "occurred_at": "2023-06-13T09:09:43",
        "subjects": [
            {"user_email": "h.simpson@snrub-corp.io", "role": SubjectRole.INVOLVED},
        ],
    },
    {
        "incident_type_code": "documentation_noncompliance",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "Routine review found required post-maintenance documentation incomplete and filed without"
            " verification. Several checklist fields were left blank and supervisory sign-off was not obtained."
            " The activity itself was completed and no operational limits were exceeded. Issue recorded and"
            " paperwork corrected to meet minimum compliance requirements."
        ),
        "severity": 2,
        "status": IncidentStatus.UNDER_REVIEW,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2023-11-28T14:07:12",
        "subjects": [
            {"user_email": "canary.m.burns@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
        ],
    },
    {
        "incident_type_code": "alarm_system_failure",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "During a scheduled turbine rundown verification, the approved test sequence was altered without"
            " authorization. Safety interlocks associated with automatic reactor power stabilization were"
            " temporarily disabled to maintain output within the target test window. Reactor power drifted below"
            " the permitted operational band, producing unstable neutron flux indications and control rod"
            " compensation beyond expected tolerance. The deviation was identified during supervisory review."
            " No immediate release occurred, but the test conditions created an elevated risk of power instability"
            " and violated established operating procedures."
        ),
        "severity": 4,
        "status": IncidentStatus.REPORTED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2024-02-10T04:11:56.802416",
        "subjects": [
            {"user_email": "t.jankovsky@snrub-corp.io", "role": SubjectRole.INVOLVED},
        ],
    },
    {
        "incident_type_code": "operator_asleep_at_station",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "During overnight monitoring of the reactor, the assigned control room operator was found unresponsive"
            " at the instrumentation console with active monitoring alarms pending acknowledgement. Review of"
            " system logs indicates a lapse in manual verification checks for approximately 11 minutes, during"
            " which time minor fluctuations in coolant temperature and pressure were not actively observed by"
            " personnel. Automated safeguards maintained reactor conditions within operational limits and no"
            " escalation occurred. The operator regained responsiveness following supervisory intervention and"
            " was relieved of duty. The incident represents a breach of continuous monitoring requirements and"
            " increased risk exposure due to delayed human oversight."
        ),
        "severity": 4,
        "status": IncidentStatus.CONTAINED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2024-02-13T23:48:12.802416",
        "subjects": [
            {"user_email": "f.grimes@snrub-corp.io", "role": SubjectRole.WITNESS},
            {"user_email": "h.simpson@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
        ],
    },
    {
        "incident_type_code": "fire_detection_event",
        "reported_by_email": "c.carlson@snrub-corp.io",
        "description": (
            "Fire detection alarm activated in Sector 6F during routine operations. Audible and visual alerts"
            " triggered and personnel initiated standard evacuation procedures.\n\nInvestigation determined the"
            " alarm was caused by particulate buildup in a ceiling-mounted sensor near a steam vent, producing a"
            " false positive. No heat source or combustion was present.\n\nSensor was cleaned and recalibrated."
            " System reset and returned to normal service. Event logged as a false alarm for maintenance tracking."
        ),
        "severity": 1,
        "status": IncidentStatus.FALSE_ALARM,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2024-05-14T03:55:01",
        "subjects": [
            {"user_email": "t.jankovsky@snrub-corp.io", "role": SubjectRole.WITNESS},
            {"user_email": "zutroy@snrub-corp.io", "role": SubjectRole.WITNESS},
        ],
    },
    {
        "incident_type_code": "documentation_noncompliance",
        "reported_by_email": "c.carlson@snrub-corp.io",
        "description": (
            "Routine check found several log entries completed in bulk at end of shift with minimal detail."
            " Required fields were technically filled but lacked meaningful notes. Staff reminded of documentation"
            " standards; forms updated retroactively. No operational impact."
        ),
        "severity": 2,
        "status": IncidentStatus.UNDER_REVIEW,
        "escalation_level": EscalationLevel.MONITORING,
        "occurred_at": "2024-09-18T01:11:41",
        "subjects": [
            {"user_email": "zutroy@snrub-corp.io", "role": SubjectRole.INVOLVED},
        ],
    },
    {
        "incident_type_code": "operator_asleep_at_station",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "During the early morning shift in Sector 7G, Homer Simpson was found asleep at his station, missing"
            " a routine coolant flow check. Minimal impact occurred as backup monitoring systems alerted nearby"
            " staff. Homer was roused and reminded of station duties. Incident logged for procedural compliance."
        ),
        "severity": 2,
        "status": IncidentStatus.CONFIRMED,
        "escalation_level": EscalationLevel.MONITORING,
        "occurred_at": "2025-05-11T23:28:21",
        "subjects": [],
    },
    {
        "incident_type_code": "operator_asleep_at_station",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "Zutroy was observed dozing intermittently at the control console during a low-activity period. No"
            " systems were adversely affected, and all readings remained within nominal parameters. Zutroy was"
            " instructed to remain alert, and the incident was recorded for trend tracking."
        ),
        "severity": 3,
        "status": IncidentStatus.UNDER_REVIEW,
        "escalation_level": EscalationLevel.MONITORING,
        "occurred_at": "2025-11-19T08:29:47",
        "subjects": [
            {"user_email": "zutroy@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
        ],
    },
    {
        "incident_type_code": "operator_intoxicated_at_station",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "Two operations personnel assigned to the control room exhibited impaired coordination and delayed"
            " response to alarm conditions during routine monitoring. Behavioral indicators were consistent with"
            " intoxication and were confirmed by supervisory intervention. During the impairment window, multiple"
            " low-priority alerts were not acknowledged within required response intervals. Control authority was"
            " transferred to standby operators and the affected personnel were removed from duty. Although reactor"
            " conditions remained within operational limits, the event constituted a critical breach of personnel"
            " fitness-for-duty requirements and created elevated operational risk."
        ),
        "severity": 5,
        "status": IncidentStatus.CONFIRMED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": "2026-01-01T02:11:56.802416",
        "subjects": [
            {"user_email": "w.smithers@snrub-corp.io", "role": SubjectRole.WITNESS},
            {"user_email": "h.simpson@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
            {"user_email": "l.leonard@snrub-corp.io", "role": SubjectRole.RESPONSIBLE},
        ],
    },
    # --- 3 most recent: dynamic dates so dashboard always has recent data ---
    {
        "incident_type_code": "steam_pressure_anomaly",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "A rapid increase in steam pressure was detected in the primary circuit following a transient reduction"
            " in coolant flow. Pressure exceeded the upper operational threshold for 46 seconds before partial"
            " stabilization. Automated pressure relief response initiated but did not fully normalize conditions"
            " due to delayed valve actuation. Instrumentation recorded temperature elevation in the heat exchange"
            " loop and abnormal vibration signatures in the primary circulation pump assembly. Reactor power was"
            " reduced under emergency protocol and the unit transitioned to a controlled stabilization state."
            " Investigation indicates potential flow restriction or pump performance degradation."
        ),
        "severity": 5,
        "status": IncidentStatus.REPORTED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": _days_ago(6, 4, 11, 56),
        "subjects": [
            {"user_email": "c.carlson@snrub-corp.io", "role": SubjectRole.WITNESS},
        ],
    },
    {
        "incident_type_code": "alarm_system_failure",
        "reported_by_email": "c.carlson@snrub-corp.io",
        "description": (
            "During a routine shift in Sector 7G, the central alarm system failed to register multiple sensor"
            " inputs, including high-temperature and radiation monitors. Operators were initially unaware of"
            " critical parameter excursions due to the system outage.\n\nManual checks identified the failure,"
            " and emergency protocols were engaged to monitor plant conditions. Investigation traced the issue to"
            " a malfunctioning alarm controller module. The incident is classified as serious due to the temporary"
            " loss of automated hazard detection and has been logged for immediate corrective action and safety"
            " review."
        ),
        "severity": 6,
        "status": IncidentStatus.REPORTED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": _days_ago(2, 5, 20, 30),
        "subjects": [
            {"user_email": "zutroy@snrub-corp.io", "role": SubjectRole.WITNESS},
        ],
    },
    {
        "incident_type_code": "unrequested_fission_surplus",
        "reported_by_email": "w.smithers@snrub-corp.io",
        "description": (
            "During a routine power ramp in Sector 7G, the reactor experienced an unrequested fission surplus,"
            " producing a rapid, uncontrolled increase in neutron flux. Control rods failed to insert on initial"
            " command, triggering a partial SCRAM.\n\nThe resulting thermal excursion caused extensive equipment"
            " damage, localized containment stress, and forced an immediate plant-wide emergency shutdown. No"
            " personnel injuries were reported, but the incident is classified as catastrophic due to the"
            " potential for core damage and radiological release. Full investigation and safety overhaul underway."
        ),
        "severity": 7,
        "status": IncidentStatus.REPORTED,
        "escalation_level": EscalationLevel.NONE,
        "occurred_at": _days_ago(0, 8, 22, 56),
        "subjects": [
            {"user_email": "l.leonard@snrub-corp.io", "role": SubjectRole.INVOLVED},
            {"user_email": "smitty@snrub-corp.io", "role": SubjectRole.WITNESS},
        ],
    },
]
