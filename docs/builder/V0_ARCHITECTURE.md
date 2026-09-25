# Autonomous Builder V0 Architecture

## Flow

```text
GOAL.md
  -> Architect route
  -> specification scope gate
  -> Implementer route
  -> controller-owned test execution
  -> isolated review copy
  -> Reviewer route
  -> SHA + acceptance criteria + test gate
  -> APPROVED or another bounded iteration
```

OmniRoute resolves provider availability and fallbacks inside each logical route. Hermes provides the role environment and tools. The Python controller is the authority for state and evidence.

Each workspace is prepared before the first model call. Generated project metadata belongs to the isolated snapshot, never to the source input.

## One Hermes, three routes

Hermes can override the model route for each invocation. A single isolated Builder profile can therefore run architect, implementer, and reviewer through different OmniRoute combos. Three Hermes installations would add state and maintenance without improving V0 isolation.

## Deliberate scope

V0 is sequential. Parallel agents, external memory, automatic merges, remote pushes, pull requests, and publication are out of scope until the basic loop has repeatable end-to-end evidence.
