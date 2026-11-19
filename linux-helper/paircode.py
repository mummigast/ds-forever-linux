"""The "Other network" code: the PC's address as digits, typed on the Thor after the 6-digit secret.

A Python copy of DS Forever's PairCode.encodeTail (dsforever/.../stream/PairCode.kt, 1.0.35); the Thor reads it with
PairCode.decodeTail. A Thor that can't see this PC's mDNS advert (WireGuard, another subnet) dials the address it carries.
The address is only where to dial: the pairing proof is keyed by the 6-digit secret alone. Pure; no I/O.
"""

DEFAULT_PORT = 48210
# kind digit, base, digits, count  (192.168/16, 10/8, 172.16/12, 100.64/10, any IPv4)
KINDS = [("1", 0xC0A80000, 5, 1 << 16), ("2", 0x0A000000, 8, 1 << 24), ("3", 0xAC100000, 7, 1 << 20),
         ("4", 0x64400000, 7, 1 << 22), ("5", 0, 10, 1 << 32)]
PORT_KIND, HOME_TAILSCALE_KIND = "6", "7"

_Q = [[0, 3, 1, 7, 5, 9, 8, 6, 4, 2], [7, 0, 9, 2, 1, 5, 4, 8, 6, 3], [4, 2, 0, 6, 8, 7, 1, 3, 5, 9],
      [1, 7, 5, 0, 9, 8, 3, 4, 2, 6], [6, 1, 2, 3, 0, 4, 5, 9, 7, 8], [3, 6, 7, 4, 2, 0, 9, 5, 8, 1],
      [5, 8, 6, 9, 7, 2, 0, 1, 3, 4], [8, 9, 4, 5, 3, 6, 2, 0, 1, 7], [9, 4, 3, 8, 6, 1, 7, 2, 0, 5],
      [2, 5, 8, 1, 4, 3, 6, 7, 9, 0]]


def damm(digits):
    x = 0
    for c in digits:
        x = _Q[x][int(c)]
    return str(x)


def mod97(digits):
    r = 0
    for c in digits:
        r = (r * 10 + int(c)) % 97
    r = r * 100 % 97
    return f"{98 - r:02d}"


def check_count(body):
    if len(body) == 6 and body[0] == "1":
        return 0
    n = (3 - len(body) % 3) % 3
    return 3 if n == 0 else n


def check(body, count):
    if count == 0:
        return ""
    if count == 1:
        return damm(body)
    if count == 2:
        d = damm(body[::-1])
        return d + damm(body + d)
    m = mod97(body)
    return m + damm(body + m)


def _ipv4(a):
    p = a.split(".")
    if len(p) != 4:
        return None
    v = 0
    for s in p:
        if not s.isdigit() or int(s) > 255:
            return None
        v = (v << 8) | int(s)
    return v


def encode_tail(addresses, port=DEFAULT_PORT):
    """The network code for the first two distinct usable IPv4 [addresses] and the bridge [port]; "" = none usable."""
    used = []
    for a in addresses:
        v = _ipv4(a)
        if v is None or v == 0 or (v >> 24) == 127 or v in used:
            continue
        used.append(v)
        if len(used) >= 2:
            break
    if not used:
        return ""
    kind = lambda v: next(k for k in KINDS if k[1] <= v < k[1] + k[3])
    body = ""
    if port != DEFAULT_PORT and 1 <= port <= 65535:
        body += PORT_KIND + f"{port:05d}"
    if len(used) == 2 and kind(used[0])[0] == "1" and kind(used[1])[0] == "4":
        body += HOME_TAILSCALE_KIND + f"{used[0] - 0xC0A80000:05d}" + f"{used[1] - 0x64400000:07d}"
    else:
        for v in used:
            k = kind(v)
            body += k[0] + str(v - k[1]).zfill(k[2])
    return body + check(body, check_count(body))


def groups(digits):
    """'700279049289390' -> '700 279 049 289 390' (as the Thor's boxes show it)"""
    return " ".join(digits[i:i + 3] for i in range(0, len(digits), 3))
