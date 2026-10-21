#!/usr/bin/env bash
MODEL=StrandsAgents/strands-decider-2B-hobson-v19
Q=(
  --noul "Does the message give a specific budget amount as a number?"
  --noul "Does the message give a specific delivery date or time frame, not just a vague word like asap?"
  --noul "Does the message list specific features, pages or deliverables to be built?"
  --noul "Does the client ask for a free sample or free trial work?"
  --noul "Does the client offer payment other than money, such as equity, exposure or future work?"
)
run() { echo "--- $1"; strands-decider ask "$MODEL" --state "$1" "${Q[@]}" 2>/dev/null; }
run "Hi, we need a website for our restaurant. Budget is around 80k PHP, we'd like it live in 6 weeks. Menu, booking form and gallery."
run "need an app asap, cheap, can you do a free sample first?"
run "Equity only for now, but great exposure. Need a full e-commerce platform."
