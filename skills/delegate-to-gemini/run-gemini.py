#!/usr/bin/env python3
"""Run agy (Gemini) read-only, with live progress and an early stop for stuck runs.

Usage: python run-gemini.py <brief.md> [--effort medium] [--model NAME] [--schema FILE]
                            [--idle 180] [--limit 600] [--resume ID]
Writes next to the brief: <name>.stream.jsonl (every event), <name>.result.md (the answer or
whatever arrived before a stop) and <name>.status.txt (how the run ended).
Exit codes: 0 finished, 2 stopped because nothing happened, 3 stopped at the time limit, 1 other.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import threading
import time


def read_event(event, pieces, state):
    """Collect answer text and the current activity from one stream event."""
    if event.get('event') == 'init':
        state['conversation'] = event.get('conversation_id', '')
    update = event.get('step_update') or {}
    if update.get('text_delta'):
        pieces.append(update['text_delta'])
    if update.get('tool_name'):
        state['last_tool'] = update['tool_name']
    result = event.get('result')
    if isinstance(result, dict) and isinstance(result.get('response'), str):
        state['final'] = result['response']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('brief')
    parser.add_argument('--effort', default='medium')
    parser.add_argument('--model')
    parser.add_argument('--schema')
    parser.add_argument('--idle', type=int, default=180)
    parser.add_argument('--limit', type=int, default=600)
    parser.add_argument('--resume')
    args = parser.parse_args()

    brief = pathlib.Path(args.brief)
    stem = brief.with_suffix('')
    stream_path = pathlib.Path(f'{stem}.stream.jsonl')
    result_path = pathlib.Path(f'{stem}.result.md')
    status_path = pathlib.Path(f'{stem}.status.txt')

    # Status tools read an empty result file and an empty .log as a running job.
    result_path.write_text('', encoding='utf-8')
    pathlib.Path(f'{stem}.log').write_text('', encoding='utf-8')

    agy = shutil.which('agy') or 'agy'
    command = [agy, '-p', brief.read_text(encoding='utf-8'), '--mode', 'plan', '--sandbox', '--add-dir', '.',
               '--output-format', 'stream-json', '--effort', args.effort, '--print-timeout', f'{args.limit}s',
               '--log-file', f'{stem}.agy-log.txt']
    if args.model:
        command += ['--model', args.model]
    if args.schema:
        command += ['--json-schema', args.schema]
    if args.resume:
        command += ['--conversation', args.resume]

    started = time.time()
    last_event = [started]
    events = [0]
    pieces = []
    state = {'conversation': '', 'last_tool': '', 'final': None}
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding='utf-8', errors='replace')

    def reader():
        with stream_path.open('w', encoding='utf-8') as stream:
            for line in process.stdout:
                last_event[0] = time.time()
                events[0] += 1
                stream.write(line)
                stream.flush()
                try:
                    read_event(json.loads(line), pieces, state)
                except (ValueError, AttributeError):
                    pass

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    ending, code = 'finished', 0
    while process.poll() is None:
        time.sleep(2)
        if time.time() - last_event[0] > args.idle:
            ending, code = f'stopped: no activity for {args.idle}s', 2
            process.kill()
        elif time.time() - started > args.limit + 30:
            ending, code = f'stopped: over the {args.limit}s limit', 3
            process.kill()
    thread.join(timeout=5)
    if code == 0 and process.returncode != 0:
        ending, code = f'agy exited with {process.returncode}', 1

    result_path.write_text(state['final'] if state['final'] is not None else ''.join(pieces), encoding='utf-8')
    summary = f'{ending}; {int(time.time() - started)}s; {events[0]} events; {result_path.stat().st_size} bytes of answer; last tool {state["last_tool"]}; conversation {state["conversation"]}'
    status_path.write_text(summary + '\n', encoding='utf-8')
    print(summary)
    sys.exit(code)


if __name__ == '__main__':
    main()
