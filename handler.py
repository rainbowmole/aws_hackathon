from strands.interventions import Guide, InterventionHandler, Proceed
from gate import decide

class LeadGate(InterventionHandler):
    """Gates the agent's send_proposal tool on the inbound inquiry."""
    name = "lead-gate"

    def __init__(self, inquiry: str):
        super().__init__()
        self.inquiry = inquiry          # start simple: we hold the inquiry text ourselves

    def before_tool_call(self, event, **kwargs):
        verdict, scores, ms = decide(self.inquiry)
        print(f"[gate] {verdict} in {ms} ms {scores}")
        if verdict == "PROCEED":
            return Proceed()
        if verdict == "ASK_FOR_DETAILS":
            return Guide(feedback="Don't send a proposal yet. Ask the client for the missing "
                                  "budget, timeline or scope.")
        # red flag or unsure: a person should look at this one
        return Guide(feedback="Do not send a proposal. Tell the client you will review their "
                              "request and follow up; flag it for the owner.")