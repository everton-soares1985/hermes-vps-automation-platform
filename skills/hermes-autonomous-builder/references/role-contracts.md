# Role contracts

## Architect

Required outputs:

- `specs/FEATURE_SPEC.md`: objective, users, scope, non-goals, constraints, acceptance criteria;
- `specs/IMPLEMENTATION_PLAN.md`: components, interfaces, data flow, risks, test strategy;
- `specs/TASKS.md`: ordered atomic tasks, dependencies, files, commands and completion conditions.

Do not edit source, tests, configuration outside `specs/`, or dependencies. Resolve ambiguity in writing; mark unresolved decisions as blockers.

## Implementer

Read all three specs before editing. Implement the smallest coherent solution. Add tests for success, failure and boundary cases. Run the commands named in the plan. Never edit `specs/` or `GOAL.md`. If the task cannot be completed, preserve partial work and report the exact blocker.

## Reviewer

Use the expected SHA in the prompt and `CONTROLLER_EVIDENCE.json`. Review the whole diff and re-run applicable tests. Write valid UTF-8 JSON at `REVIEW.json` matching the schema in the role prompt. Use `CHANGES_REQUESTED` when:

- any required behavior is unverified;
- a critical or high finding exists;
- tests fail or were not actually executed;
- the evidence references another SHA;
- files are outside the authorized scope.

Never edit implementation or test files in the review copy.
