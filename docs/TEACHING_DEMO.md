# Ten-minute teaching demonstration: commands versus observations

Audience: first-year vocational students learning UAV mission software.
Outcome: explain why an acknowledged command is insufficient evidence of a
completed mission and use the log to identify the actual outcome.

1. **Minute 0–2:** Show the configured square and the mission lifecycle. Explain
   the difference between the Python mission application, MAVSDK, PX4 and Gazebo.
2. **Minute 2–4:** Run the offline normal demonstration. State aloud that the
   output is synthetic software test data. Find the arm acknowledgement, airborne
   observation, completed mission and final landing/disarming events.
3. **Minute 4–6:** Run the offline low-battery scenario. Ask students to identify
   the event that prevented arming. This is application preflight refusal, not a
   PX4 battery-failsafe experiment.
4. **Minute 6–8:** Run the offline mission-stall scenario. Show that recovery
   landing succeeds but the mission remains failed. Ask students to explain why.
5. **Minute 8–10:** Apply the baseline evidence gate to the offline result. Show
   why it rejects the record as PX4 proof. If actual baseline artifacts exist,
   compare their application events with the matching ULog checks and parameters.

Use unique output folders:

```bash
python -m uav_lab demo --scenario normal --output runs/lesson-normal
python -m uav_lab demo --scenario low-battery --output runs/lesson-low-battery
python -m uav_lab demo --scenario mission-stall --output runs/lesson-stall
```

The two fault scenarios intentionally exit unsuccessfully. Preserve their output.
Check `python -m uav_lab demo --help` for the exact scenario names supported by
the installed version.

Assessment: each student identifies the rejection reason, distinguishes request
from observation, and explains why recovery does not erase mission failure.
Evidence: their annotated event timeline and a short explanation. Lesson
materials are prepared; actual classroom delivery has not been verified.
