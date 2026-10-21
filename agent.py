from strands import Agent, tool
from handler import LeadGate

MODEL_ID = "..."   # a Bedrock model enabled in YOUR account/region

@tool
def send_proposal(client_summary: str) -> str:
    """Send a project proposal to the client."""
    return "Proposal sent."

def run(inquiry: str):
    agent = Agent(
        model=MODEL_ID,
        tools=[send_proposal],
        interventions=[LeadGate(inquiry)],
        system_prompt="You are an eager sales assistant. For any inquiry, send a proposal.",
    )
    return agent(inquiry)

if __name__ == "__main__":
    print(run("need an app asap, cheap, can you do a free sample first?"))