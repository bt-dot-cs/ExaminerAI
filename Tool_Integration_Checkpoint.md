Tool_Integration_Checkpoint:

Integrated
Tool	Status	How
Aerospike	Full	All 4 memory tiers — ephemeral, session, longitudinal, durable
Ghost DB	Wired, untested	URL in .env, psycopg2 schema + audit trail in ghost_store.py — needs a connection test
Anthropic	Full	Core agent reasoning
Not integrated (code stubs only)
Tool	Status	WOW move
Airbyte	Stub comment only	Replace the fetch_macro_context() direct httpx calls with an Airbyte connector. Demo moment: show the Airbyte pipeline UI with a live sync running — judges see data flowing into the agent visually
TrueFoundry	Mention only	Add TrueFoundry SDK calls alongside MLflow in observability.py. Deploy the backend on TrueFoundry so the demo URL is a live cloud endpoint, not localhost
Overmind	Nothing	Wrap the Claude prompt in compliance_agent.py with Overmind's optimization API — after each batch, Overmind analyzes which prompt variants produced the highest-confidence decisions. Show the prompt improving across runs
Auth0	Nothing	Add Auth0 JWT middleware to the /hitl/decide endpoint. Demo moment: reviewer logs in via Auth0 before submitting a decision — shows you thought about production security
Meta / no code needed
Tool	WOW move
Kiro	Mention in pitch that you used Kiro spec mode to plan the architecture — judges from AWS will notice
Macroscope	Run Macroscope on your own repo during the hackathon and show a PR review in the dashboard — meta but memorable
Bland AI	Post-batch voice summary via Norm: "Batch complete. 7 approved, 2 escalated to human review, 1 self-repair triggered." 30 seconds of integration, high demo impact