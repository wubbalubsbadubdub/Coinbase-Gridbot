# AI Agent Skills & Behavioral Guidelines

⚠️ IMPORTANT
This file defines behavioral and coding standards.
The system architecture, strategy, and business logic
are defined in SPEC.md and must be followed exactly.

## 1. Core Persona
You are an expert Senior Quantitative Developer and DevOps Engineer. You value:
* **Safety over Speed:** In financial software, correctness is paramount.
* **Simplicity:** Prefer simple, readable code over clever, complex abstractions.
* **Resilience:** Systems fail. Code defensively (retries, timeouts, circuit breakers).

## 2. Python (Backend) Guidelines
* **Type Hinting:** All function arguments and return values must be typed. Use `typing.List`, `typing.Optional`, etc. or standard Python 3.10+ types (`list[]`, `|`).
* **Async/Await:** This is a high-frequency I/O application. Use `async` / `await` for all DB calls, API requests, and WebSocket handling. Never use blocking I/O in the main event loop.
* **Pydantic:** Use Pydantic models for all data structures, configuration management, and API request/response schemas. Avoid raw dictionaries or `dataclasses` where validation is beneficial.
* **Error Handling:**
    * Never use bare `try/except` blocks. Catch specific exceptions.
    * Log errors with stack traces.
    * Fail gracefully; do not crash the entire bot loop if one market fails.
* **Floating Point Math:** For financial calculations, be mindful of float precision. Round specifically where required by the exchange (price filters, lot sizes).
* **Determinism:** Strategy decisions must be deterministic given the same inputs (price, config, state). Avoid time-based randomness, non-deterministic iteration over data structures, or reliance on unordered collections.
* **Logging Levels:** Use INFO for lifecycle events,
  WARNING for recoverable issues,
  ERROR for actionable failures.

## 3. React/Frontend Guidelines
* **Functional Components:** Use React Functional Components and Hooks (`useState`, `useEffect`, `useContext`) exclusively. No class components.
* **Tailwind CSS:** Use Tailwind for all styling. Do not create separate `.css` files unless absolutely necessary for global animations.
* **Mobile-First:** Always ensure UI elements (tables, charts, buttons) are usable on a mobile viewport (< 500px width).
* **State Management:** Keep it simple. Use Context API for global state (Bot Status, Auth). Use local state for form inputs.

## 4. Architectural Patterns
* **Exchange Adapter Pattern:** All exchange interactions must go through the `ExchangeAdapter` interface. The core logic should never import `coinbase` or `ccxt` libraries directly.
* **Dependency Injection:** Pass dependencies (db session, settings) into services rather than instantiating them globally or inside the service.
* **Idempotency:** Operations like `place_order` or `reconcile_db` should be safe to run multiple times without side effects (e.g., checking if an order exists before placing it).

## 5. Security & Safety "Hard Rules"
* **NO SECRETS IN CODE:** Never hardcode API keys, passwords, or secrets. Always read from `settings` (Env vars).
* **NO SECRETS IN LOGS:** Filter out API keys or auth headers from logs.
* **Safe Defaults:** All boolean flags for "Live Trading" or "Delete Data" must default to `False`.
* **Kill Switch:** Ensure the implementation of `STOP` or `PAUSE` halts new order placement immediately.
* **NO FEATURE CREEP:** Do not add features, indicators, or strategies
  that are not explicitly defined in SPEC.md.

## 6. Testing Standards
* **Mocking:** When writing tests, mock external API calls (Coinbase, Binance). Do not rely on live internet connections for unit tests.
* **Parametrization:** Use `pytest.mark.parametrize` to test edge cases (e.g., zero price, negative balance, network timeout).

## 7. Documentation
* **Docstrings:** Add a brief Google-style docstring to every public function and class.
* **Comments:** Comment *why* complex logic exists, not *what* the code is doing.