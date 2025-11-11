# Checklists

This file contains checklists of things that must be done when implementing a specific kind of feature. Developers
are encouraged to follow the checklist to not forget anything before posting a PR. The checklists may be handy for
LLM agents to make a review or implement missing steps.

If no proper feature category is here, it may be added if needed.

## Adding new endpoint to the Pylon service

* Add the endpoint
* Add endpoint tests in tests/service:
  * success (with and without optional parameters if applicable)
  * edge cases (for example empty response, edge parameters etc.)
  * validation errors
  * other possible errors
* All a PylonRequest and a PylonResponse for the Pylon client.
  * PylonRequest should be used as an input data for write endpoints (unless it does not contain any parameters)
  * Implement a proper translation for PylonRequest in the Pylon client
  * Expose the PylonRequest and PylonResponse by the public interface (apiver)
* Add tests for the pylon client in tests/client:
  * proper response from api (with and without optional parameters if applicable)
  * edge cases if any applicable
  * pylon request validation errors
  * other possible errors
* Check if the information in README is not stale.
