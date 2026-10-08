"""Append-only run evidence and an offline HTML report. No external assets."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import csv
import hashlib
import html
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any

from . import __version__
from .config import MissionConfig
from .model import Snapshot


def write_json(path: Path, value: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def source_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


class Recorder:
    def __init__(self, output: Path, config: MissionConfig, backend: str, extra: dict | None = None) -> None:
        # Reuse of a directory is prohibited: never silently overwrite evidence.
        output.mkdir(parents=True, exist_ok=False)
        self.output, self.config, self.backend = output, config, backend
        self.samples: list[dict] = []
        self.events: list[dict] = []
        self.csv_file = (output / "telemetry.csv").open("w", newline="", encoding="utf-8")
        self.events_file = (output / "events.jsonl").open("w", encoding="utf-8")
        self.writer = csv.DictWriter(self.csv_file, fieldnames=["elapsed_s", "phase", *Snapshot.__dataclass_fields__])
        self.writer.writeheader()
        self.csv_file.flush()
        packages = {}
        for name in ("mavsdk-grpc", "grpcio", "protobuf"):
            try:
                packages[name] = metadata.version(name)
            except metadata.PackageNotFoundError:
                packages[name] = None
        config_bytes = json.dumps(config.to_dict(), sort_keys=True).encode()
        manifest = {
            "project_version": __version__, "backend": backend,
            "data_kind": "synthetic software test data" if backend == "offline-demo" else "PX4 SITL telemetry (operator-confirmed)",
            "time_basis": "virtual demo seconds" if backend == "offline-demo" else "host monotonic seconds",
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "python": sys.version, "platform": platform.platform(), "packages": packages,
            "source_sha256": source_digest(), "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "metadata": extra or {},
            "limitations": [
                "No physical-drone validation.",
                "Host-receipt samples are not time-synchronised sensor ground truth.",
                "Route limits are not an onboard geofence; return altitude depends on PX4 settings.",
            ],
        }
        write_json(output / "manifest.json", manifest)
        write_json(output / "config.json", config.to_dict())

    def event(self, elapsed_s: float, kind: str, detail: str = "") -> None:
        event = {"elapsed_s": round(elapsed_s, 6), "event": kind, "detail": detail}
        self.events.append(event)
        self.events_file.write(json.dumps(event, allow_nan=False) + "\n")
        self.events_file.flush()

    def sample(self, elapsed_s: float, phase: str, snapshot: Snapshot) -> None:
        snapshot.validate()
        record = {"elapsed_s": round(elapsed_s, 6), "phase": phase, **asdict(snapshot)}
        self.samples.append(record)
        self.writer.writerow(record)
        self.csv_file.flush()

    def finish(self, result: dict) -> dict:
        result = {
            **result, "backend": self.backend,
            "recorded_samples": len(self.samples),
            "observed_max_altitude_m": max((s["relative_altitude_m"] for s in self.samples), default=None),
            "observed_min_battery_fraction": min((s["battery_fraction"] for s in self.samples), default=None),
        }
        self.csv_file.close()
        self.events_file.close()
        write_json(self.output / "summary.json", result)
        (self.output / "report.html").write_text(render_report(self.config.name, result, self.events), encoding="utf-8")
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(self.output.iterdir()) if p.is_file() and p.name != "SHA256SUMS.json"}
        write_json(self.output / "SHA256SUMS.json", hashes)
        return result


def render_report(name: str, summary: dict, events: list[dict]) -> str:
    esc = lambda x: html.escape(str(x), quote=True)
    synthetic = summary["backend"] == "offline-demo"
    warning = ("OFFLINE DEMO — Synthetic software test data. No PX4 or Gazebo flight was run."
               if synthetic else "PX4 SITL — Simulation telemetry, not physical flight experience.")
    rows = "".join(f"<tr><th scope='row'>{esc(key.replace('_', ' '))}</th><td>{esc(value)}</td></tr>"
                   for key, value in summary.items())
    timeline = "".join(f"<tr><td>{e['elapsed_s']:.2f}</td><td>{esc(e['event'])}</td><td>{esc(e['detail'])}</td></tr>"
                       for e in events)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>UAV Lab report — {esc(name)}</title>
<style>
body{{font:16px/1.6 system-ui,sans-serif;max-width:980px;margin:40px auto;padding:0 24px}}
h1{{font-size:2.1rem;line-height:1.2;margin-bottom:12px}}h2{{margin-top:36px}}
.notice{{border:2px solid;padding:16px;font-weight:600}}.eyebrow{{letter-spacing:.12em;font-size:.8rem}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{padding:10px 12px;border-bottom:1px solid #ccc;text-align:left;vertical-align:top;overflow-wrap:anywhere}}
.summary th{{width:48%}}.scroll{{overflow-x:auto}}code{{font-family:monospace}}footer{{margin-top:40px;border-top:1px solid;padding-top:16px;font-size:.85rem}}
@media print{{body{{margin:0;max-width:none}}thead{{display:table-header-group}}tr{{break-inside:avoid}}}}
</style></head><body>
<p class="eyebrow">UAV MISSION TEACHING LAB / RUN EVIDENCE</p>
<h1>{esc(name)}</h1><p class="notice">{esc(warning)}</p>
<p>The report separates command requests from observed outcomes. A failed mission remains failed even when recovery landing succeeds.</p>
<h2>Outcome</h2><div class="scroll"><table class="summary"><tbody>{rows}</tbody></table></div>
<h2>Event timeline</h2><div class="scroll"><table><thead><tr><th>Elapsed seconds</th><th>Event</th><th>Detail</th></tr></thead><tbody>{timeline}</tbody></table></div>
<h2>Evidence files</h2><p><a href="telemetry.csv">Telemetry CSV</a> · <a href="events.jsonl">Events JSONL</a> · <a href="manifest.json">Environment and provenance</a> · <a href="config.json">Mission configuration</a> · <a href="summary.json">Machine-readable result</a></p>
<h2>Interpretation</h2><p>Altitude and battery are sampled observations, not a full-rate flight log. No trajectory-accuracy or safety-certification claim is made. Archive the PX4 ULog and parameter export separately for a simulator experiment.</p>
<footer>Version {__version__}. Simulation-only educational prototype. No real-drone commands are supported by this project.</footer>
</body></html>"""
