import json, urllib.request

URL = "http://localhost:8000/v1/systemone"
YES, NO = 0.70, 0.30   # between these = "unsure"

QUESTIONS = {
    "has_budget":   "Does the message give a specific budget amount as a number?",
    "has_timeline": "Does the message give a specific delivery date or time frame, not just a vague word like asap?",
    "has_scope":    "Does the message list specific features, pages or deliverables to be built?",
    "free_sample":  "Does the client ask for a free sample or free trial work?",
    "non_cash_pay": "Does the client offer payment other than money, such as equity, exposure or future work?",
}

def ask(state):
    body = {"state": state,
            "questions": {k: {"type": "noul", "instructions": q} for k, q in QUESTIONS.items()}}
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"content-type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def label(p):
    return "yes" if p >= YES else "no" if p <= NO else "unsure"

def decide(state):
    resp = ask(state)
    scores = {k: resp["answers"][k]["noul"] for k in QUESTIONS}
    lab = {k: label(p) for k, p in scores.items()}
    if lab["free_sample"] == "yes" or lab["non_cash_pay"] == "yes":
        verdict = "REVIEW_RED_FLAG"        # human confirms any decline
    elif any(lab[k] == "no" for k in ("has_budget", "has_timeline", "has_scope")):
        verdict = "ASK_FOR_DETAILS"
    elif "unsure" in lab.values():
        verdict = "HUMAN_REVIEW"
    else:
        verdict = "PROCEED"
    return verdict, scores, resp.get("latency_ms")

if __name__ == "__main__":
    for s in [
        "Hi, we need a website for our restaurant. Budget is around 80k PHP, we'd like it live in 6 weeks. Menu, booking form and gallery.",
        "need an app asap, cheap, can you do a free sample first?",
        "Equity only for now, but great exposure. Need a full e-commerce platform.",
    ]:
        v, sc, ms = decide(s)
        print(f"{v:16} {ms} ms  {s[:50]}...")