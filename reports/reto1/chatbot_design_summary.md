# Chatbot Design Summary - Reto 1

## Core Design Decisions
- Chatbot never computes analytics directly
- Planner schema gates execution
- Clarification rules prevent unsafe assumptions
- Language rules enforce non-causal framing
- Chat state remains minimal and explicit

## Implementation Readiness
| phase | component | depends_on | status |
| --- | --- | --- | --- |
| 1 | planner + intent router | NB20 intents/configs | ready_to_build |
| 2 | tool adapter layer | deterministic functions + NB30 outputs | ready_to_build |
| 3 | response renderer | response_contract + language rules | ready_to_build |
| 4 | chat state manager | chat_state_schema | ready_to_build |
| 5 | golden flow tests | golden_flows + evaluation framework | ready_to_build |
| 6 | streamlit app shell | phases 1-5 | pending_implementation |