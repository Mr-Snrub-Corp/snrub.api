from app.models.incident_report import EscalationLevel, IncidentStatus
from app.models.incident_report_subject import SubjectRole

INCIDENT_REPORTS = [
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
        "occurred_at": "2026-02-12T04:11:56.802416",
        "subjects": [
            {"user_email": "c.carlson@snrub-corp.io", "role": SubjectRole.WITNESS},
        ],
    },
]
