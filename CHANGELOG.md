# Changelog

All notable changes to Project Odin are documented in this file.

## [0.8.2]

### Changed

- Extracted reusable frontend domain types, formatting helpers, chart controls, and interval controls.
- Centralized frontend API requests and endpoint access behind a typed service.
- Improved client-side handling for network failures, non-JSON responses, and failed emergency actions.
- Standardized interactive control styling, focus states, and disabled states.
- Improved narrow-screen layouts for navigation, tables, scanner actions, strategy controls, and account views.
- Reformatted and simplified backend service and route code to remove duplicated response construction.

### Compatibility

- No business logic, API endpoints, request payloads, response schemas, or trading behavior changed.
