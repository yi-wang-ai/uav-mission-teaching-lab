# Roadmap and honest completion gates

## M0 — application foundation (this release)

Configuration, mission orchestration, offline demonstrations, reports, tests and
a written lesson are present. Actual local results are recorded in
`../VALIDATION.md`. The PX4 adapter is implemented but not yet flight-validated.

## M1 — reproduce the first actual PX4 baseline (next)

Install the pinned stack on a suitable Linux host. Pass the optional API-contract
tests, then record three closed-route missions from a known starting state.
Archive reports, configs, ULogs, parameters, environment and source revisions.
Write an explanation of each transition in the observed flight.

Acceptance is evidence-based, not “the code ran without an exception.”
Do not count a GitHub fork, the supplied fake data or generated code as flight
reproduction. Keep the project marked “in progress” until genuine evidence exists.

## M2 — one actual PX4 failsafe experiment

Choose ONE fault after baseline reliability is established. Form a hypothesis,
record the relevant onboard parameter values, inject the fault only in
simulation and compare the ULog with the expected response.

For battery, distinguish a preflight application refusal from an airborne PX4
battery failsafe. For communication loss, identify the exact link being lost:
RC, ground-station data link and offboard-command delivery are different. This
project uses a mission, not continuous offboard control. Stopping Python does
not necessarily stop another process or QGroundControl from sending heartbeats.
Use independent onboard evidence rather than assuming that missing telemetry
means the drone landed. See the PX4 failsafe reference.

No actual fault injection is automated or validated by v0.1.0.

## M3 — make one teaching demonstration

Use a validated baseline/fault pair to make a short captioned demonstration,
revise the worksheet and record any genuine teaching feedback. Do not claim
“teaching experience” merely because the lesson document exists.

## M4 — GitHub and CV

Review code and records before publishing. Keep PX4 as an attributed dependency;
commit the application, tests and selected non-sensitive evidence, not vendor
source, virtual environments or fabricated results. The ZIP has not been pushed
to a GitHub account.

Only describe work that you personally reviewed, ran, understood or extended.
Name AI assistance and upstream work accurately where relevant. Simulation work
does not establish a UAV licence or physical flight-work eligibility.
