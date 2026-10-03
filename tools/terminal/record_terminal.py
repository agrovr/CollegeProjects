"""Record a console program in a pseudo-terminal while typing scripted keys.

    python tools/terminal/record_terminal.py demo.json 104 30 tools/terminal/scripts/pet-demo.json -- ./build/virtual-pet --seed 5

The script is a JSON list of [milliseconds, keys] pairs. Keys are sent as typed text, so
"\\r" is Enter, "\\u001b" is Escape and "\\u001b[C" is the right arrow. The recording holds
every output chunk with its timestamp, ready for render_terminal.py. POSIX only.
"""

import base64
import fcntl
import json
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time


def main():
    if "--" not in sys.argv or len(sys.argv) < 6:
        sys.exit(__doc__)
    out, columns, rows, script_path = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    command = sys.argv[sys.argv.index("--") + 1:]
    with open(script_path, encoding="utf-8") as handle:
        script = json.load(handle)
    end_ms = script[-1][0] + 1500

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
    env = dict(os.environ, TERM="xterm-256color", COLORTERM="truecolor")
    process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, env=env, close_fds=True)
    os.close(slave)

    chunks, start, index = [], time.time(), 0
    while True:
        now = (time.time() - start) * 1000
        while index < len(script) and script[index][0] <= now:
            os.write(master, script[index][1].encode())
            index += 1
        if now > end_ms or (process.poll() is not None and not select.select([master], [], [], 0)[0]):
            break
        ready, _, _ = select.select([master], [], [], 0.01)
        if ready:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            chunks.append([now, base64.b64encode(data).decode()])
    if process.poll() is None:
        process.kill()

    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"cols": columns, "rows": rows, "chunks": chunks, "duration": (time.time() - start) * 1000}, handle)
    print(f"{len(chunks)} chunks recorded to {out}")


if __name__ == "__main__":
    main()
