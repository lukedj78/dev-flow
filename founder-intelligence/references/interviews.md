# Customer discovery

The skill prepares the interviews and makes sense of the notes. It never conducts one and never invents one.
The quality of what is learned depends on two things: the questions, and whether they reach the right people.

## Who to talk to

A precise profile beats a long contact list: job title, company type and size, team structure, seniority,
and the situation in which the problem appears. Then where those people actually are (communities, events,
LinkedIn groups, Slack or Discord workspaces, the founder's own network) and an order of outreach by how close
each group is to the problem. When the hypothesis involves more than one persona (a finance manager and a
CFO, a user and a buyer), each gets its own question set.

## What to ask

About the **past**, not the future. "Would you use something like this?" invites a polite yes; "tell me about
the last time you dealt with this" produces evidence.

- The last time it happened: what triggered it, what they did, how long it took, what it cost.
- What they use today, what they tried before, what made them stop.
- Who else is involved, and who decides on spending.
- What they have already paid or built to deal with it.

Draft the questions, then audit them: flag any that is leading, about the future, too broad, or likely to get
a socially desirable answer. For the two or three moments most likely to produce a deflection, prepare a
follow-up probe.

## Notes

One file per interview, written or pasted by the founder: `.workflow/founder/interviews/NN-<who>.md`.

```markdown
# NN — <role, company type> — <date>
- Profile match: <how close to the target profile>
- Context: <how they were reached>
## What they said
<notes, quotes marked as quotes>
## Supports the hypothesis
## Challenges the hypothesis
## Surprising
```

## Synthesis, every five interviews

1. Two lists: the evidence that supports the hypothesis and the evidence that challenges it, each item
   pointing to its interview file.
2. If the first list is much longer, check whether the asymmetry is in the notes or in the reading of them.
3. Recurring themes and contradictions; the strongest signal in each direction.
4. Update §5, the confidence column of §16, and §18 if a decision changes.

Five interviews are a checkpoint, not a proof. Problem-solution fit is a judgement on the pattern across
them: is the problem real and specific, does the solution answer the problem the interviews revealed (not
the one first assumed), and is there enough signal to justify building an MVP?
