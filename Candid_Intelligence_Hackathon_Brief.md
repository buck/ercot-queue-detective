## **What we're building this weekend**

Candid builds the AI engineering execution layer for capital projects in power and energy infrastructure. Everyone treats the engineering itself as the hard part. It isn't. The harder part is *knowing which projects are real, which are early, and who is driving them* — before anyone else does. That intelligence is what lets you win the right work at the right moment instead of showing up late to a competitive bid.

Over this hackathon we're building two pieces of that intelligence layer, for real. Not toy demos — running systems that ingest messy public data and turn it into signal we could actually use on Monday.

Pick a track. Build something that works, and make it something people can't stop looking at. The best builds — and the best builders — don't go unnoticed.

## **The thesis: origination**

In energy infrastructure, origination is the front end of the deal funnel: finding projects and the people behind them *early*, while they're still at the concept or feasibility stage, long before an RFP goes out. Whoever sees a project first and already knows the decision-maker wins it on relationship and timing, not on price.

The two tracks are the two halves of an origination engine — the projects and the people. Build either one well. Build a way to join them, and you've built the whole thing (there's a bonus for that).

*(Track names are working titles. Rename them, brand them, do whatever you want.)*

---

## **Track 1 — Project Radar**

### Origination: the projects

There is no single live source of truth for capital projects moving through the U.S. energy pipeline. The information exists, but it's scattered across a dozen disconnected systems — interconnection queues, utility-commission dockets, environmental permits, county agendas, equipment orders, earnings calls, trade press. A single project appears in each of these at different times, often under a different LLC or project name at each stage. Today, building the full picture of one project means a human hopping between five websites and guessing at the connections.

This track has two jobs, and you need both to win.

Job one — parse and aggregate. Ingest all of these sources and unify them into one clean dataset. The hard, valuable parts are *entity resolution* (recognizing that a project name, a permit filed under a holding company, and an interconnection request are the same project) and *stage inference* (working out where each project sits: concept select → FEL-1 → FEL-2 / pre-FEED → FEED → interconnection agreement → FID → construction → COD). Attach a confidence level to each stage call and keep the source filings that justify it. And keep it live — this updates itself, it isn't a one-time scrape.

Job two — present it so it's addictive. This is not a bonus; it's half the point. The output should be a live map / dashboard that a non-technical person can open and immediately understand — and want to keep watching. Think the feel of monitorthesituation.com: satisfying to explore, updating in real time, easy to lose an hour in. Someone should be able to click one project and see its entire stitched-together story across every source on a single screen.

Sources to start with (all public):

- ERCOT — the monthly Generator Interconnection Status (GIS) report and the RIOO interconnection-request system; the MORA report for resource-adequacy context.  
- PUCT — the Interchange filing/docket system for Texas utility-commission activity.  
- FERC — eLibrary for federal filings.  
- Environmental permits — TCEQ air-permit database in Texas (analogous state agencies elsewhere).  
- Ground-level early signals — Railroad Commission of Texas, county commissioners' court agendas, municipal permitting.  
- Equipment and finance — OEM/EPC press releases and order announcements, project-finance news.  
- Earnings calls — scan developer and utility transcripts for named projects and timelines.

What a winning build looks like:

- It runs and stays current on its own. Liveness is the single most important quality here.  
- The visualization is genuinely intuitive and addictive — you'd open it for fun.  
- Entity resolution works on the hard cases (same project, different names).  
- Bonus: stage-change alerts, linked news articles, and a lens focused on what we care about — early-stage gas-to-power and behind-the-meter data-center power.

Prior art to study (don't clone): [https://monitor-the-situation.com/](https://monitor-the-situation.com/) for the *feel*; ercotqueue.com for a domain-specific take on the interconnection queue. Your edge over both is liveness, cross-source entity resolution, and stage inference — presented better than either.

---

## **Track 2 — Speaker Signal**

### Origination: the people, and the motion to reach them

The right buyers — VPs of Engineering and project-delivery leaders at lean owner-operators and developers — tell you who they are in public. They get on stage at energy conferences and talk about exactly the projects they're working on. There's no automated way to keep up with the conference calendar, pull the speakers, qualify them, and actually run the outreach. That last part is where this track goes further than just a list.

Two jobs here too.

Job one — aggregate and visualize. Maintain a self-updating calendar of energy conferences (most recur annually, so seed the recurring ones and detect new events as they're announced). When a new event or agenda is published, parse the site to extract each speaker's name, title, and company, and score every speaker against Candid's ICP. Capture *what they're speaking about* — the session topic is itself a signal; someone on "behind-the-meter power for AI data centers" is a hotter lead than someone on a generic sustainability panel. Then present all of it in one place, in the same addictive, explorable spirit as Track 1: a single view of every upcoming event and every ICP-fit person on it, ranked, with the reason each one matters.

This is tractable because the sites hand you the data — conference schedule pages publish each speaker's name *and* company directly. Data Center World Power's agenda, for instance, lists sessions as speaker name plus organization, right on the page. Good starting venues: Data Center World Power, DTECH Data Centers & AI, CERAWeek, Gastech, POWERGEN, Reuters Events energy summits, and Infocast's power / data-center summits.

Job two — the sequence (the GTM motion). A list isn't the goal; a *motion* is. Once a speaker is identified, turn them into a timed outreach campaign, and make that campaign a first-class, visible thing. Juicebox (the AI recruiting tool) is the reference: candidates it finds flow straight into multi-step, personalized email sequences, and a Sequences view tracks open, reply, and meeting rates. Borrow that pattern — but anchor the cadence to the conference date instead of an arbitrary schedule:

- T–2 weeks: first touch.  
- T–1 week: follow-up.  
- T–2 days: "let's meet at the event" nudge.  
- At the event: meet in person.  
- Post-event: follow-up to book a real conversation.

Then visualize the whole funnel and its drop-off at each step — identified → contacted → replied → meeting scheduled → met at the event → follow-up sent → conversation booked — so you can see exactly where the motion leaks. That funnel *is* the GTM motion, made legible.

What a winning build looks like:

- Point it at a conference URL and get back a scored, deduplicated, enriched list of ICP-fit speakers with their talk topics.  
- Identified speakers flow into event-anchored outreach sequences with drafted, personalized emails.  
- A funnel view shows conversion and drop-off at every stage.  
- The calendar maintains itself; new events appear without a human adding them.

A note on doing this right: public data only, respect each site's terms, and keep outreach genuinely personalized and compliant (real relevance, easy opt-out — not a spam cannon). The whole point is that these are the right people talking about the right thing; treat them that way.

---

## **Bonus — the combined database**

### One place for the projects *and* the people

The two tracks are worth far more together than apart. The prize build is a single database where the projects (Track 1\) and the companies and people (Track 2\) live in one place, joined: a speaker maps to their company, and their company maps to its live projects and the stage each is in.

That join pays off both directions. For any upcoming conference, surface the speakers whose companies have live early-stage projects — ranked by how good a conversation they'd be *right now* — and let Track 2's outreach sequence prioritize itself off that project intelligence. Or run it the other way: for any hot early-stage project, find which people from that company are speaking somewhere soon, so you know exactly who to go meet.

That's origination in one screen: the right person, the right project, the right moment. The strongest Track 1 and Track 2 teams are encouraged to pair up at the end and demo this joined view.

---

## **How we'll judge**

- Liveness and robustness — does it actually run, and (for the aggregation work) stay current on its own?  
- Presentation — is it intuitive and addictive? We mean it. A build people want to keep looking at beats a technically-correct one nobody opens twice.  
- Signal quality — are the outputs accurate and genuinely useful? Precision beats volume; a short list of *right* answers beats a long list of noise.  
- Depth on the hard part — entity resolution, stage inference, the sequencing/funnel logic. We're most impressed by teams that took on the genuinely difficult piece instead of routing around it.  
- Extensibility — could this credibly become production infrastructure, not just a weekend artifact?  
- The Candid ethos — does it feel like an owner's engineer running at software speed?

---

## **Logistics**

- Dates / hours: Saturday 8/8/2026  
- Venue: Museum District, Houston. Details here: https://luma.com/m7sk0hyv  
- Team size: 👥 Teams of 2-4. We'll help solo builders form teams at kickoff.  
- What to bring: your laptop, and any API keys or accounts you want to use.  
- Submission: a working demo plus a short README covering what you built, the sources you used, and what you'd build next with another week.  
- Prizes: 🏆$1,750 in cash prizes: $1,000 / $500 / $250

Questions before or during — reach out to talha@candidintelligence.com.

---

## **One more thing**

These are the actual problems the intelligence side of Candid runs on. Build something real this weekend — something live, something people can't stop looking at — and you'll have shown us exactly the kind of work we do here every day. The people who impress us won't have to wonder what comes next.

Let's build. — Candid Intelligence  
