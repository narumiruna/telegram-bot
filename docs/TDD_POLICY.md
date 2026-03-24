# TDD Policy

- Non-trivial changes MUST start with a test.
- A test MUST fail before implementation begins (red → green → refactor).
- Implementation MUST follow the red → green → refactor cycle strictly.
- Implement the smallest change required to make the test pass.
- Refactoring MUST happen only after tests pass and MUST NOT change behavior.

- Tests MUST act as executable specifications of behavior, not merely coverage.
- Tests MUST assert observable behavior, not implementation details.

- Bug fixes MUST include a regression test when feasible.
- Code changes SHOULD include corresponding test updates when behavior changes.

- Tests MUST be deterministic and isolated (no uncontrolled network, time, randomness).
- Unit tests MUST NOT cross process boundaries (network, DB, external services).
- External dependencies MUST be mocked or stubbed.

- Tests SHOULD target the lowest meaningful level (unit > integration > e2e).
- Integration and end-to-end tests MUST complement unit tests where needed.

- Tests MUST NOT be weakened or removed to satisfy incorrect implementations.
- Tests SHOULD fail for a single clear reason.

- When tests cannot be added, this MUST be rare and explicitly justified, including:
  - why testing is not feasible
  - what risk remains
  - how the change was validated

- Skipping TDD for non-trivial changes REQUIRES explicit justification.

## Scope

- Non-trivial changes include:
  - Bug fixes
  - New features
  - Behavior changes
  - Data transformations
  - Business logic or query changes

- Excluded:
  - Pure formatting changes
  - Renames without behavior change
  - Comment or documentation updates

### Exceptions

- TDD MAY be relaxed for:
  - Rapid prototyping or spike solutions
  - Exploratory coding where requirements are unclear
  - Pure UI layout or styling changes
