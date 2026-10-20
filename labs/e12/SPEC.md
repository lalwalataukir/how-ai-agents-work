# Spec: <your project's name>

**One line:** <who it helps, with what, in one sentence>
**Author:** <you> · **Date:** <today> · **Status:** draft

## The problem
<Who has this problem, how often, and what they do today. Two or three sentences.>

## The user and the main flow
- **User:** <one specific person, ideally you>
- **They ask or do:** <the request, in their words>
- **They get:** <the result, and how they can check it>

## Success measures
| Measure | Target | How it's measured |
|---|---|---|
| Eval score | at least 85% | `run_evals.py`, in CI on every pull request |
| Cost | under $1 per 1,000 questions | `compare_models.py` and the Anthropic Console |
| First words on screen | under 5 seconds | the web app's timing line |

## Scope
- **Must (version 1):** <the one flow, end to end, deployed>
- **Should (if time allows):** <one or two things>
- **Won't (not now):** <the tempting things you're leaving out>

## How it works
<Tools, data sources and model, in a few bullets. Name the E-modules each part comes from.>

## Risks and limits
- **Security:** <what could be attacked, and which E10 defences cover it>
- **Wrong answers:** <what happens when it's wrong, and how the user can tell>
- **Cost:** <the limits in code, and the spend limit in the Console>

## Evals
<What the eval set covers, including questions it should refuse or can't answer.>
