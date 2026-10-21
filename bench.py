import statistics, time
from gate import ask

S = "Hi, we need a website for our restaurant. Budget is around 80k PHP, we'd like it live in 6 weeks. Menu, booking form and gallery."

for _ in range(3):          # warm-up
    ask(S)

server, wall = [], []
for _ in range(30):
    t = time.perf_counter()
    r = ask(S)
    wall.append((time.perf_counter() - t) * 1000)
    server.append(r["latency_ms"])

def p(xs, q): return sorted(xs)[int(q * (len(xs) - 1))]
print(f"server p50 {p(server, .5):.0f} ms  p95 {p(server, .95):.0f} ms")
print(f"wall   p50 {p(wall, .5):.0f} ms  p95 {p(wall, .95):.0f} ms")