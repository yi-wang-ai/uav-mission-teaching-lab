"""Run three baseline missions on a dedicated Linux PX4/Gazebo host.

No hardware devices or bridges may be attached. Keeps every failed attempt.
Build/setup must be completed first. Stops at the first failure.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from uav_lab.evidence import PIN, audit_baseline, audit_run, audit_flight_samples


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT / 'vendor/PX4-Autopilot'), *args], text=True).strip()


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)


def inspect_ulog(path):
    from pyulog import ULog
    log = ULog(str(path))
    landed = log.get_dataset('vehicle_land_detected').data['landed']
    armed = log.get_dataset('vehicle_status').data['arming_state']
    finished = log.get_dataset('mission_result').data['finished']
    checks = audit_flight_samples(landed, armed, finished, int(log.initial_parameters.get('SYS_AUTOSTART', -1)))
    return checks, log.initial_parameters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-sitl', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.confirm_sitl or platform.system() != 'Linux':
        parser.error('Requires --confirm-sitl on a dedicated Linux simulator host')
    if git('rev-parse', 'HEAD') != PIN or git('status', '--porcelain', '--untracked-files=no'):
        parser.error('Expected a clean pinned PX4 source checkout')
    submodules = git('submodule', 'status', '--recursive')
    if any(line.startswith(('-', '+', 'U')) for line in submodules.splitlines()):
        parser.error('PX4 submodules are missing or differ from pinned revisions')
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    rootfs = ROOT / 'vendor/PX4-Autopilot/build/px4_sitl_default/rootfs'
    if not rootfs.is_dir():
        parser.error('Build PX4 first with DONT_RUN=1 make px4_sitl gz_x500')
    runs = []
    for index in range(1, 4):
        folder = args.output / f'run-{index:02d}'
        folder.mkdir()
        before = {p: p.stat().st_mtime_ns for p in rootfs.rglob('*.ulg')}
        provenance = {'px4_commit': git('rev-parse', 'HEAD'), 'submodules': submodules,
                      'application_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                      'platform': platform.platform(), 'physical_hardware': False,
                      'simulator_restarted_for_run': True}
        (folder / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        simulator = None
        try:
            with (folder / 'simulator.txt').open('w') as output:
                simulator = subprocess.Popen(['bash', str(ROOT / 'scripts/start_px4.sh')], cwd=ROOT,
                                             stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + 180
                while 'Ready for takeoff' not in (folder / 'simulator.txt').read_text(errors='replace'):
                    if simulator.poll() is not None:
                        raise RuntimeError('Simulator exited before readiness; inspect simulator.txt')
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Simulator readiness timeout; checks were not bypassed')
                    time.sleep(1)
                with (folder / 'runner.txt').open('w') as runner_output:
                    subprocess.run([sys.executable, '-m', 'uav_lab', 'px4', '--confirm-sitl',
                                    '--config', str(ROOT / 'configs/square.json'), '--output', str(folder / 'mission')],
                                   cwd=ROOT, stdout=runner_output, stderr=subprocess.STDOUT, check=True, timeout=600)
        finally:
            if simulator is not None:
                stop(simulator)
            # Retain simulator logs even on failure; never manufacture missing ULogs.
            import shutil
            for path in rootfs.rglob('*.ulg'):
                if path not in before or path.stat().st_mtime_ns != before[path]:
                    target = folder / 'ulogs' / path.relative_to(rootfs)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
        ulogs = list((folder / 'ulogs').rglob('*.ulg'))
        if len(ulogs) != 1:
            raise RuntimeError(f'Expected one matching ULog, found {len(ulogs)}; inspect retained files')
        checks, parameters = inspect_ulog(ulogs[0])
        (folder / 'ulog-checks.json').write_text(json.dumps(checks, indent=2) + '\n')
        (folder / 'parameters.json').write_text(json.dumps(parameters, indent=2, default=str) + '\n')
        checksums = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(folder.rglob('*')) if p.is_file()}
        (folder / 'archive-sha256.json').write_text(json.dumps(checksums, indent=2) + '\n')
        if not all(checks.values()) or not audit_run(folder / 'mission')['accepted']:
            raise RuntimeError('Baseline evidence did not pass; inspect application and ULog checks')
        runs.append(folder / 'mission')
    result = audit_baseline(runs)
    result['independent_ulog_checks_passed'] = True
    (args.output / 'baseline.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
