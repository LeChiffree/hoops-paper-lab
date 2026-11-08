"""Generic protobuf dump (no schema) for the AiScore matches feed."""
import sys, json

def read_varint(b, i):
    x = 0; s = 0
    while True:
        c = b[i]; i += 1
        x |= (c & 0x7f) << s
        if not (c & 0x80): return x, i
        s += 7

def try_msg(b):
    i = 0; out = []
    try:
        while i < len(b):
            k, i = read_varint(b, i)
            f, w = k >> 3, k & 7
            if w == 0:
                v, i = read_varint(b, i)
                out.append((f, "v", v))
            elif w == 2:
                ln, i = read_varint(b, i)
                if i + ln > len(b): return None
                out.append((f, "b", b[i:i+ln])); i += ln
            elif w == 5:
                out.append((f, "f32", b[i:i+4])); i += 4
            elif w == 1:
                out.append((f, "f64", b[i:i+8])); i += 8
            else:
                return None
    except Exception:
        return None
    return out if out else None

def show(b, depth=0, maxdepth=6, prefix="", maxitems=40):
    fields = try_msg(b)
    if fields is None:
        return False
    for f, t, v in fields[:maxitems]:
        pad = "  " * depth
        if t == "v":
            print(f"{pad}{f}: {v}")
        elif t == "f32":
            print(f"{pad}{f}: f32 {v.hex()}")
        elif t == "f64":
            print(f"{pad}{f}: f64 {v.hex()}")
        else:
            sub = try_msg(v) if depth < maxdepth and len(v) > 0 else None
            printable = None
            try:
                s = v.decode("utf-8")
                if s.isprintable() and len(s) > 1:
                    printable = s
            except Exception:
                pass
            if printable and (sub is None or len(printable) < 40):
                print(f"{pad}{f}: str {printable!r}")
            elif sub is not None:
                print(f"{pad}{f}: msg ({len(v)}b)")
                show(v, depth+1, maxdepth, prefix, maxitems)
            else:
                print(f"{pad}{f}: bin({len(v)}) {v[:40].hex()}")
    return True

if __name__ == "__main__":
    path = sys.argv[1]
    b = open(path, "rb").read()
    print("bytes", len(b))
    show(b, 0, int(sys.argv[2]) if len(sys.argv) > 2 else 5, maxitems=int(sys.argv[3]) if len(sys.argv) > 3 else 25)
