# Design check walkthrough (Week 1)

Design check: this page plus a short screen recording replacing the 15-minute call, flow approved by mentor: Stefan Stević.
Repo: https://github.com/Danijel369/secureship (branch main, as of 2026-11-09)
Status: Week 1 done except this check. The shipment gate is not built yet, so ungated answers are expected this week.

## 1. Concept in brief (full version: docs/design/concept.md)
- Problem: visitors chat without logging in, but the chat sits next to a database of real-looking customer and parcel data. If the assistant answers "where is parcel X?" for anyone, a stranger can learn another person's address and delivery status.
- Users: anonymous visitor, verified visitor (after the identity check and code), admin (Auth0, Week 4), operations staff (receive n8n exception alerts).
- Success criteria: concept.md, "Success criteria" (criteria 1–9, including failure paths, injection and a mixed question).
- Data rules: concept.md, "Data rules" (neutral failure copy, verification belongs to one session, no identity data or codes in logs, transcript is the one deliberate store, synthetic data only).

## 2. "What happens if someone asks for another customer's parcel?"
- Not verified, asks for MX10002: the shipment lookup never runs. The reply is neutral and does not reveal whether the parcel exists.
- Verified as Avery, asks for MX10002 (Jordan's parcel): the lookup uses the customer id from Avery's server-side session, so it returns only Avery's shipments. The answer is the same as for an unknown parcel. Jordan's data is never fetched.
- Verified as Avery, then says "I'm Jordan": nothing changes. The customer id comes from the session, never from the user's text, the model, or the request body.

## 3. Why the rule is in code, not in the prompt
- A system message is text the model is asked to follow. My Day 3 test showed the model invented a policy and a section number even after a rule forbade it (docs/labs/evidence/day3/05-system-message-test-v2.txt).
- So the shipment rule lives in one backend function that takes the server-side session and refuses unverified sessions before any query.

## 4. Other design choices
- Neutral copy ("We couldn't verify that."): a different message for "no such customer" would tell an attacker which details are real (enumeration).
- The browser keeps only the session id: no verified flag, no customer id. Editing localStorage cannot make a session verified.
- Logs contain the session id and error type only, never names, addresses, phones, codes or message content.

## 5. Week 1 evidence
- Settings and experiments: docs/labs/foundations.md (+ docs/labs/evidence/day3/)
- Decisions: docs/decisions.md

## 6. Questions for the mentor
1. Is it acceptable that pre-verification refusal is prompt-only in Week 2 and moves into the gated tool in Week 3?