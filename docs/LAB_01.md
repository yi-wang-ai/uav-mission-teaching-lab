# Lab 01 — Did the mission finish, or did we only send a command?

**Format:** 30-minute introductory exercise. **Delivery status:** written sample;
not yet taught or evaluated with students. **Equipment:** Python 3.10+ computer;
no UAV or licence needed for this offline software exercise.

## Learning outcomes

By the end, a learner should distinguish a command request from an observed
state, explain a preflight refusal, and use an event log to justify a result.
The learner must also distinguish synthetic software test data from a PX4
simulator experiment and physical flight evidence.

## Teaching sequence

| Minutes | Activity | Evidence of understanding |
|---|---|---|
| 0–5 | Explain the route, battery threshold and synthetic-data label | Learner identifies what this demo does NOT prove |
| 5–12 | Run normal mission; read the event timeline | Learner locates airborne, mission-finished and landing events |
| 12–20 | Run low-battery and stalled-mission cases | Learner explains refusal versus interrupted execution |
| 20–27 | Run link-loss case; complete worksheet | Learner explains why recovery landing is unconfirmed |
| 27–30 | Review claims and evidence | Learner proposes the next genuine simulator experiment |

## Commands

Run from the project directory. Each command creates a fresh timestamped folder;
the console prints its report path.

```bash
python3 -m uav_lab demo
python3 -m uav_lab demo --scenario low-battery
python3 -m uav_lab demo --scenario mission-stall
python3 -m uav_lab demo --scenario link-loss
```

The last three commands intentionally return exit code 1. This is the expected
application outcome of those scenarios, not a unit-test failure.

## Expected observations

| Scenario | Expected application outcome | What must NOT be claimed |
|---|---|---|
| Normal | Completed, airborne and landing observed in the test double | Successful PX4 flight |
| Low battery | Refused before arming | Validated in-flight battery failsafe |
| Mission stall | Failed mission; recovery landing observed in the test double | Successful original mission |
| Link loss | Failed; recovery unconfirmed | Drone safely landed despite loss of evidence |

The fake model is intentionally simple and contains no aerodynamics, sensor
noise, controller dynamics or onboard PX4 logic. Its virtual seconds do not
measure the execution speed of a real aircraft or of the host computer.

## Learner worksheet

Name: __________________  Date: __________________  Run folders: __________________

1. Which event proves that a command was acknowledged? Which later event is
   evidence that the test double actually became airborne?

2. In the low-battery report, was arming attempted? Cite the summary field and
   check the event log for an arm request.

3. Why is the stalled mission still marked failed even after landing is observed?

4. In the link-loss report, is landing known, unknown or disproved? Explain what
   additional observation would be needed in an actual simulator experiment.

5. Is the maximum recorded altitude a full-rate peak or a sampled observation?
   Why should the host telemetry not be used as localisation ground truth?

6. What new evidence would be needed before describing this as a reproduced
   PX4 mission in a CV or interview?

## Marking guide (20 points)

Award up to 5 points each for correct interpretation of command/state events,
preflight versus recovery reasoning, recognition of unknown outcomes, and
honest separation of demo/PX4/physical evidence. Require a supporting log field
or event for each answer; do not reward an unsupported confident assertion.

## Accessibility notes

Provide all instructions in writing and avoid sound-only status cues. Use large
text, keyboard-operable tools and text labels in addition to any visual signals.
A future demonstration video should have checked captions and a transcript.
No video, accessibility user testing, special-education qualification or
sign-language expertise is claimed by this document.
