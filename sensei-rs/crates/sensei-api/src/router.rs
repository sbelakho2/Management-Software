//! Top-level router configuration.
//!
//! Assembles the Axum router with all routes, middleware layers, and
//! shared application state.
//!
//! # Middleware execution order
//!
//! Layers are applied bottom-to-top; the **last** layer added runs **first**
//! (outermost). Global stack, outermost → innermost:
//!
//! `secure_headers → cors → request_id → logging → trace → metrics →
//! inject_rate_limiter → rate_limit_middleware → request_guard →
//! request_body_limit → compression → router`
//!
//! Note that `inject_rate_limiter` is **outer** to `rate_limit_middleware`
//! so the `RateLimiter` is in the request extensions before the limiter
//! runs.
//!
//! # Streaming routes and the request timeout
//!
//! The global `TimeoutLayer` would kill long-lived streaming connections,
//! so it is applied to a **nested** router that contains only non-streaming
//! routes. The real-time routes (`/api/v1/ws`, `/api/v1/sse`) and the
//! protected streaming route (`/api/v1/chat/stream`) are merged *outside*
//! the timeout: they still pass through every other middleware layer.
//!
//! Protected-route stack (via `route_layer`), outermost → innermost:
//!
//! `auth → session_binding → idempotency → audit → handler`
//!
//! So authentication runs first (making `AuthenticatedUser` available to
//! session binding, idempotency key scoping, and audit recording), and the
//! audit middleware runs closest to the handler so it can time it.

use axum::{
    extract::Request,
    http::StatusCode,
    middleware,
    middleware::Next,
    response::{Html, IntoResponse, Json, Response},
    routing::{delete, get, patch, post, put},
    Router,
};
use std::sync::Arc;
use std::time::Duration;
use tower_http::compression::CompressionLayer;
use tower_http::limit::RequestBodyLimitLayer;
use tower_http::services::ServeDir;
use tower_http::timeout::TimeoutLayer;
use tower_http::trace::TraceLayer;

use crate::middleware::audit::audit_middleware;
use crate::middleware::auth::auth_layer;
use crate::middleware::cors::build_cors_layer;
use crate::middleware::idempotency::{idempotency_middleware, IdempotencyStore};
use crate::middleware::logging::logging_middleware;
use crate::middleware::metrics::metrics_middleware;
use crate::middleware::rate_limiter::rate_limit_middleware;
use crate::middleware::request_guard::{request_guard_middleware, RequestGuardConfig};
use crate::middleware::request_id::request_id_middleware;
use crate::middleware::secure_headers::secure_headers_middleware;
use crate::middleware::session::session_binding_middleware;
use crate::routes;
use crate::state::AppState;

/// Wrapper middleware that injects the [`RateLimiter`] from `AppState` into
/// request extensions so [`rate_limit_middleware`] can find it.
///
/// Must run **before** [`rate_limit_middleware`] (i.e. be added *after* it),
/// which is why this layer is outer to the limiter in [`build_router`].
async fn inject_rate_limiter(
    axum::extract::State(state): axum::extract::State<AppState>,
    req: Request,
    next: Next,
) -> Response {
    let mut req = req;
    req.extensions_mut().insert(state.rate_limiter.clone());
    next.run(req).await
}

/// Catch-all handler for unmatched `/api/*` paths.
///
/// Registered before the [`ServeDir`] fallback so unknown API endpoints
/// return a structured JSON 404 instead of falling through to the static
/// frontend (which would serve the SPA HTML for API requests).
async fn api_not_found() -> Response {
    (
        StatusCode::NOT_FOUND,
        Json(serde_json::json!({
            "error": "not_found",
            "message": "Unknown API endpoint",
        })),
    )
        .into_response()
}

/// Landing-page handler for `GET /`.
///
/// Returns a minimal HTML page confirming the API is running and linking to
/// the health-check endpoints.  When the Leptos WASM frontend has been built
/// (via `scripts/build-frontend-wasm.sh`) and its output placed in the static
/// directory, the browser will load the full SPA instead.
async fn root_handler() -> Html<&'static str> {
    Html(ROOT_HTML)
}

/// Static HTML served at `/` when no WASM frontend is available.
///
/// Styled according to the Sensei-RAMS Industrial Functionalist design system
/// (v3.0). Uses the dark-mode warm-grey palette, 4px grid, sharp borders,
/// and the "control station" metaphor.
static ROOT_HTML: &str = r##"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sensei OS — Control Station</title>
  <style>
    /* ── Sensei-RAMS Design Tokens (Dark Mode) ────────────────────── */
    :root {
      --rams-chassis:    #1A1A1A;
      --rams-module:     #252525;
      --rams-panel:      #2D2D2D;
      --rams-line:       #404040;
      --rams-muted:      #666666;
      --rams-foreground: #F2F2F2;
      --rams-orange:     #FFBE00;
      --rams-green:      #2D8C3C;
      --rams-red:        #D62D2D;
      --rams-steel:      #4A90E2;
    }

    /* ── Reset & Base ─────────────────────────────────────────────── */
    *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
      background: var(--rams-chassis);
      color: var(--rams-foreground);
      min-height: 100vh;
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      font-feature-settings: "kern" 1, "liga" 1;
      line-height: 24px;
      font-size: 16px;
      padding-bottom: 40px;
    }

    /* ── Skip Link (Accessibility) ────────────────────────────────── */
    .skip-link {
      position: absolute;
      top: -48px;
      left: 0;
      padding: 8px 16px;
      background: var(--rams-orange);
      color: #000;
      font-weight: 600;
      font-size: 14px;
      z-index: 9999;
      transition: top 0.2s;
      text-decoration: none;
    }
    .skip-link:focus { top: 0; }

    /* ── Industrial Bezel Frame ───────────────────────────────────── */
    .bezel {
      position: fixed;
      inset: 0;
      border: 8px solid var(--rams-chassis);
      pointer-events: none;
      z-index: 100;
    }
    .screw {
      position: fixed;
      z-index: 101;
      opacity: 0.3;
      user-select: none;
      pointer-events: none;
    }
    .screw-tl { top: 4px; left: 4px; }
    .screw-tr { top: 4px; right: 4px; }
    .screw-bl { bottom: 36px; left: 4px; }
    .screw-br { bottom: 36px; right: 4px; }

    /* ── Status Bar ───────────────────────────────────────────────── */
    .status-bar {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: 32px;
      background: var(--rams-chassis);
      border-top: 1px solid var(--rams-line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      z-index: 100;
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 10px;
      line-height: 14px;
      color: var(--rams-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
    }
    .status-bar-group { display: flex; gap: 24px; }

    /* ── Layout ───────────────────────────────────────────────────── */
    .page {
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 24px;
    }

    /* ── Station Header ───────────────────────────────────────────── */
    .station-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--rams-line);
      margin-bottom: 32px;
      flex-wrap: wrap;
      gap: 16px;
    }
    .station-id {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .station-icon {
      width: 40px;
      height: 40px;
      background: var(--rams-panel);
      border: 1px solid var(--rams-line);
      border-radius: 2px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      font-weight: 700;
      color: var(--rams-foreground);
    }
    .station-name {
      font-size: 20px;
      font-weight: 700;
      line-height: 28px;
      letter-spacing: -0.01em;
    }
    .station-subtitle {
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 10px;
      line-height: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
      color: var(--rams-muted);
    }
    .station-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      background: var(--rams-module);
      border: 1px solid var(--rams-line);
      border-radius: 2px;
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 10px;
      line-height: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
      color: var(--rams-green);
    }
    .station-badge-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--rams-green);
      box-shadow: 0 0 8px rgba(45,140,60,0.5);
    }

    /* ── Tagline ──────────────────────────────────────────────────── */
    .tagline {
      font-size: 14px;
      line-height: 20px;
      color: var(--rams-muted);
      margin-bottom: 32px;
      max-width: 640px;
    }

    /* ── Module (Card Replacement) ────────────────────────────────── */
    .module {
      background: var(--rams-module);
      border: 1px solid var(--rams-line);
      border-radius: 2px;
    }
    .module-header {
      padding: 12px 16px;
      border-bottom: 1px solid var(--rams-line);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .module-title {
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 10px;
      line-height: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
      color: var(--rams-muted);
    }
    .module-content { padding: 16px; }

    /* ── System Status Panel ──────────────────────────────────────── */
    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }
    .status-metric {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .status-metric-label {
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 10px;
      line-height: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
      color: var(--rams-muted);
    }
    .status-metric-value {
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 24px;
      line-height: 32px;
      font-weight: 700;
      font-variant-numeric: tabular-nums lining-nums;
      color: var(--rams-foreground);
    }
    .status-metric-unit {
      font-size: 12px;
      line-height: 16px;
      color: var(--rams-muted);
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
    }

    /* ── Andon Stack ──────────────────────────────────────────────── */
    .andon-stack {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 4px;
      background: var(--rams-panel);
      border: 1px solid var(--rams-line);
      border-radius: 2px;
    }
    .andon-light {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--rams-muted);
      opacity: 0.2;
    }
    .andon-light.active-red   { background: var(--rams-red);    opacity: 1; }
    .andon-light.active-yellow{ background: var(--rams-orange); opacity: 1; }
    .andon-light.active-green { background: var(--rams-green);  opacity: 1; box-shadow: 0 0 8px rgba(45,140,60,0.5); }

    /* ── Quick Links Grid ─────────────────────────────────────────── */
    .links-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 4px;
      margin-bottom: 32px;
    }
    .link-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: var(--rams-module);
      border: 1px solid var(--rams-line);
      border-radius: 2px;
      text-decoration: none;
      color: var(--rams-foreground);
      font-size: 14px;
      font-weight: 500;
      transition: border-color 100ms ease-out, background-color 100ms ease-out;
    }
    .link-item:hover {
      border-color: var(--rams-muted);
      background: var(--rams-panel);
    }
    .link-item:focus-visible {
      outline: none;
      box-shadow: 0 0 0 2px var(--rams-orange);
    }
    .link-item:active {
      transform: scale(0.98);
    }
    .link-indicator {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--rams-muted);
      opacity: 0.3;
      flex-shrink: 0;
    }
    .link-item:hover .link-indicator { opacity: 1; background: var(--rams-orange); }
    .link-path {
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 12px;
      color: var(--rams-muted);
      margin-left: auto;
    }

    /* ── API Modules Overview ─────────────────────────────────────── */
    .modules-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 4px;
    }
    .api-module {
      padding: 16px;
      background: var(--rams-module);
      border: 1px solid var(--rams-line);
      border-radius: 2px;
      transition: border-color 100ms ease-out;
    }
    .api-module:hover { border-color: var(--rams-muted); }
    .api-module-name {
      font-size: 14px;
      font-weight: 600;
      line-height: 20px;
      margin-bottom: 4px;
    }
    .api-module-desc {
      font-size: 12px;
      line-height: 16px;
      color: var(--rams-muted);
    }
    .api-module-count {
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 10px;
      line-height: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
      color: var(--rams-steel);
      margin-top: 8px;
    }

    /* ── Section Spacing ──────────────────────────────────────────── */
    .section { margin-bottom: 32px; }
    .section-label {
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 10px;
      line-height: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
      color: var(--rams-muted);
      margin-bottom: 12px;
      padding-left: 2px;
    }

    /* ── API Base Indicator ───────────────────────────────────────── */
    .api-base {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: var(--rams-panel);
      border: 1px solid var(--rams-line);
      border-radius: 2px;
      font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
      font-size: 12px;
      color: var(--rams-foreground);
    }
    .api-base-label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
      color: var(--rams-muted);
    }

    /* ── Reduced Motion ───────────────────────────────────────────── */
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
      }
    }

    /* ── Responsive ───────────────────────────────────────────────── */
    @media (max-width: 640px) {
      .bezel, .screw, .status-bar { display: none; }
      body { padding-bottom: 0; }
      .page { padding: 16px; }
      .station-header { flex-direction: column; align-items: flex-start; }
      .status-grid { grid-template-columns: 1fr 1fr; }
      .links-grid { grid-template-columns: 1fr; }
      .modules-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (min-width: 641px) and (max-width: 1024px) {
      .modules-grid { grid-template-columns: repeat(3, 1fr); }
    }
  </style>
</head>
<body>
  <!-- Skip Link -->
  <a href="#main" class="skip-link">Skip to main content</a>

  <!-- Industrial Bezel Frame -->
  <div class="bezel" aria-hidden="true"></div>
  <div class="screw screw-tl" aria-hidden="true">&#x271A;</div>
  <div class="screw screw-tr" aria-hidden="true">&#x271A;</div>
  <div class="screw screw-bl" aria-hidden="true">&#x271A;</div>
  <div class="screw screw-br" aria-hidden="true">&#x271A;</div>

  <!-- Status Bar -->
  <footer class="status-bar" role="contentinfo" aria-label="System status bar">
    <div class="status-bar-group">
      <span>STATION: SENSEI-API-01</span>
      <span>OS: 3.0.0-RAMS</span>
    </div>
    <div class="status-bar-group">
      <span>STATUS: OPERATIONAL</span>
      <span id="clock"></span>
    </div>
  </footer>

  <!-- Main Content -->
  <main id="main" role="main" aria-label="Sensei OS Control Station" class="page">

    <!-- Station Header -->
    <header class="station-header" role="banner">
      <div class="station-id">
        <div class="station-icon" aria-hidden="true">&#x25A3;</div>
        <div>
          <div class="station-name">SENSEI OS</div>
          <div class="station-subtitle">Manufacturing Control Station</div>
        </div>
      </div>
      <div class="station-badge" role="status" aria-label="System status: Operational">
        <div class="station-badge-dot" aria-hidden="true"></div>
        OPERATIONAL
      </div>
    </header>

    <!-- Tagline -->
    <p class="tagline">
      High-precision manufacturing management API. Less, but better &#x2014;
      industrial functionalism for production, quality, maintenance, and beyond.
    </p>

    <!-- System Status Panel -->
    <section class="section" aria-labelledby="status-heading">
      <div class="section-label" id="status-heading">SYSTEM STATUS</div>
      <div class="module">
        <div class="module-content">
          <div class="status-grid">
            <div class="status-metric">
              <div class="status-metric-label">API Status</div>
              <div class="status-metric-value" style="color: var(--rams-green);">&#x2713; UP</div>
            </div>
            <div class="status-metric">
              <div class="status-metric-label">Version</div>
              <div class="status-metric-value">3.0.0</div>
              <div class="status-metric-unit">RAMS Design System</div>
            </div>
            <div class="status-metric">
              <div class="status-metric-label">API Base</div>
              <div class="status-metric-value" style="font-size: 16px; line-height: 24px;">/api/v1/</div>
              <div class="status-metric-unit">REST + WebSocket</div>
            </div>
            <div class="status-metric" style="display: flex; flex-direction: row; align-items: center; gap: 16px;">
              <div>
                <div class="status-metric-label">Health</div>
                <div class="status-metric-value" style="font-size: 16px; line-height: 24px; color: var(--rams-green);">OPTIMAL</div>
              </div>
              <!-- Andon Stack -->
              <div class="andon-stack" role="status" aria-label="Andon status: Green (operational)">
                <div class="andon-light" aria-hidden="true"></div>
                <div class="andon-light" aria-hidden="true"></div>
                <div class="andon-light active-green" aria-hidden="true"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Quick Links -->
    <section class="section" aria-labelledby="links-heading">
      <div class="section-label" id="links-heading">DIAGNOSTICS</div>
      <nav aria-label="API diagnostic endpoints">
        <div class="links-grid">
          <a href="/health/live" class="link-item" aria-label="Liveness probe">
            <div class="link-indicator" aria-hidden="true"></div>
            <span>Liveness Probe</span>
            <span class="link-path">/health/live</span>
          </a>
          <a href="/health/ready" class="link-item" aria-label="Readiness probe">
            <div class="link-indicator" aria-hidden="true"></div>
            <span>Readiness Probe</span>
            <span class="link-path">/health/ready</span>
          </a>
          <a href="/health/detailed" class="link-item" aria-label="Detailed health check">
            <div class="link-indicator" aria-hidden="true"></div>
            <span>Detailed Health</span>
            <span class="link-path">/health/detailed</span>
          </a>
          <a href="/metrics" class="link-item" aria-label="Prometheus metrics">
            <div class="link-indicator" aria-hidden="true"></div>
            <span>Prometheus Metrics</span>
            <span class="link-path">/metrics</span>
          </a>
        </div>
      </nav>
    </section>

    <!-- API Modules Overview -->
    <section class="section" aria-labelledby="modules-heading">
      <div class="section-label" id="modules-heading">API MODULES</div>
      <div class="modules-grid">
        <div class="api-module">
          <div class="api-module-name">Production</div>
          <div class="api-module-desc">Work orders, production orders, BOM, MRP</div>
          <div class="api-module-count">10 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Quality</div>
          <div class="api-module-desc">NCRs, CAPAs, audits, inspections, FMEA, gauges</div>
          <div class="api-module-count">30 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Maintenance</div>
          <div class="api-module-desc">Work requests, PM schedules, equipment</div>
          <div class="api-module-count">12 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Finance</div>
          <div class="api-module-desc">Invoices, payments, budgets, journal entries</div>
          <div class="api-module-count">12 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Supply Chain</div>
          <div class="api-module-desc">RFQs, quotes, sales orders, POs, inventory</div>
          <div class="api-module-count">18 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">HR</div>
          <div class="api-module-desc">Employees, training, leave, reviews, timecards</div>
          <div class="api-module-count">16 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Operations</div>
          <div class="api-module-desc">Andon, projects, A3 problem solving, risks</div>
          <div class="api-module-count">12 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Inventory</div>
          <div class="api-module-desc">Items, stock moves, warehouses, stats</div>
          <div class="api-module-count">5 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Work Orders</div>
          <div class="api-module-desc">Orders, operations, status tracking, stats</div>
          <div class="api-module-count">6 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Work Centers</div>
          <div class="api-module-desc">Centers, capacity, efficiency reporting</div>
          <div class="api-module-count">5 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Kanban</div>
          <div class="api-module-desc">Boards, columns, cards, metrics</div>
          <div class="api-module-count">8 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">AI / ML</div>
          <div class="api-module-desc">Anomaly detection, quality & maintenance prediction</div>
          <div class="api-module-count">4 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Training</div>
          <div class="api-module-desc">Courses, enrollments, dashboards</div>
          <div class="api-module-count">7 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Quoting</div>
          <div class="api-module-desc">RFQs, quotes, versions, AI-assisted costing</div>
          <div class="api-module-count">10 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">KPI / CTQ</div>
          <div class="api-module-desc">Key indicators, critical-to-quality, dashboards</div>
          <div class="api-module-count">8 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Lean</div>
          <div class="api-module-desc">LSW standards, standard work, state machines</div>
          <div class="api-module-count">12 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Admin</div>
          <div class="api-module-desc">System health, DB stats, user management, logs</div>
          <div class="api-module-count">6 endpoints</div>
        </div>
        <div class="api-module">
          <div class="api-module-name">Platform</div>
          <div class="api-module-desc">Auth, users, tenants, search, notifications, attachments</div>
          <div class="api-module-count">18 endpoints</div>
        </div>
      </div>
    </section>

  </main>

  <!-- Clock Script -->
  <script>
    (function() {
      var el = document.getElementById('clock');
      function tick() {
        var d = new Date();
        var h = String(d.getUTCHours()).padStart(2,'0');
        var m = String(d.getUTCMinutes()).padStart(2,'0');
        var s = String(d.getUTCSeconds()).padStart(2,'0');
        el.textContent = h + ':' + m + ':' + s + ' UTC';
      }
      tick();
      setInterval(tick, 1000);
    })();
  </script>
</body>
</html>"##;

/// Build the complete Axum application router.
///
/// # Arguments
/// * `state` - The shared application state.
///
/// # Returns
/// A configured [`Router`] ready to be served.
pub fn build_router(state: AppState) -> Router {
    let cors_layer = build_cors_layer(&state.config);

    // ── Shared instances for middleware infrastructure ──────────────
    let idempotency_store = Arc::new(IdempotencyStore::with_pool(
        3600, // 1 hour TTL
        state.db_pool.clone(),
    ));
    let request_guard_config = Arc::new(RequestGuardConfig {
        max_body_size: state.config.api.body_limit,
        request_timeout_secs: state.config.api.request_timeout_secs,
        ..Default::default()
    });

    // ── Public routes (no auth required) ────────────────────────────
    let public_routes = Router::new()
        .route("/livez", get(routes::health::liveness))
        .route("/readyz", get(routes::health::readiness))
        .route("/health/live", get(routes::health::liveness))
        .route("/health/ready", get(routes::health::readiness))
        .route("/health/detailed", get(routes::health::detailed))
        .route("/api/v1/auth/login", post(routes::auth::login))
        .route("/api/v1/auth/refresh", post(routes::auth::refresh))
        .route("/api/v1/auth/register", post(routes::auth::register))
        .route(
            "/api/v1/auth/password-reset/request",
            post(routes::auth::request_password_reset),
        )
        .route(
            "/api/v1/auth/password-reset/confirm",
            post(routes::auth::confirm_password_reset),
        )
        .route(
            "/api/v1/auth/verify-email/request",
            post(routes::auth::request_email_verification),
        )
        .route(
            "/api/v1/auth/verify-email/confirm",
            post(routes::auth::confirm_email_verification),
        )
        .route("/metrics", get(routes::metrics::metrics_handler));

    // ── Real-time streaming routes (NO request timeout) ─────────────
    // Long-lived WS/SSE connections must never be killed by the timeout
    // layer, so they live in a dedicated router merged outside it.
    let realtime_routes = Router::new()
        .route("/api/v1/ws", get(routes::ws::ws_handler))
        .route("/api/v1/sse", get(routes::ws::sse_handler));

    // ── Protected routes (auth required) ───────────────────────────
    let protected_routes = Router::new()
        // ── Auth Routes (protected) ─────────────────────────────────
        .route("/api/v1/auth/logout", post(routes::auth::logout))
        .route(
            "/api/v1/auth/me",
            get(routes::auth::get_me).put(routes::auth::update_me),
        )
        .route(
            "/api/v1/auth/me/password",
            put(routes::auth::change_password),
        )
        // ── Users Routes ────────────────────────────────────────────
        .route("/api/v1/users", get(routes::users::list_users))
        .route(
            "/api/v1/users/{id}",
            get(routes::users::get_user)
                .put(routes::users::update_user)
                .delete(routes::users::deactivate_user),
        )
        .route(
            "/api/v1/users/{id}/activate",
            put(routes::users::activate_user),
        )
        .route(
            "/api/v1/users/{id}/roles",
            put(routes::users::update_user_roles),
        )
        // ── Tenants Routes ──────────────────────────────────────────
        .route(
            "/api/v1/tenants",
            get(routes::tenants::list_tenants).post(routes::tenants::create_tenant),
        )
        .route(
            "/api/v1/tenants/{id}",
            get(routes::tenants::get_tenant).put(routes::tenants::update_tenant),
        )
        // ── Accounts Routes ─────────────────────────────────────────
        .route(
            "/api/v1/accounts",
            get(routes::accounts::list_accounts).post(routes::accounts::create_account),
        )
        .route(
            "/api/v1/accounts/{id}",
            get(routes::accounts::get_account)
                .put(routes::accounts::update_account)
                .delete(routes::accounts::delete_account),
        )
        // ── Contacts Routes ─────────────────────────────────────────
        .route(
            "/api/v1/contacts",
            get(routes::contacts::list_contacts).post(routes::contacts::create_contact),
        )
        .route(
            "/api/v1/contacts/{id}",
            get(routes::contacts::get_contact)
                .put(routes::contacts::update_contact)
                .delete(routes::contacts::delete_contact),
        )
        // ── Products Routes ─────────────────────────────────────────
        .route(
            "/api/v1/products",
            get(routes::products::list_products).post(routes::products::create_product),
        )
        .route(
            "/api/v1/products/{id}",
            get(routes::products::get_product)
                .put(routes::products::update_product)
                .delete(routes::products::delete_product),
        )
        // ── AI / ML Routes ────────────────────────────────────────
        .route(
            "/api/v1/ai/anomalies/detect",
            post(routes::ai::detect_anomalies),
        )
        .route(
            "/api/v1/ai/quality/predict",
            post(routes::ai::predict_quality),
        )
        .route(
            "/api/v1/ai/maintenance/predict",
            post(routes::ai::predict_maintenance),
        )
        .route("/api/v1/ai/models/retrain", post(routes::ai::retrain_model))
        // ── Chatbot Routes ─────────────────────────────────────────
        .route("/api/v1/chat", post(routes::chatbot::chat))
        // ── Realtime Routes (protected) ─────────────────────────────
        // Mints one-time WS/SSE connection tickets (authenticated).
        .route(
            "/api/v1/realtime/ticket",
            post(routes::ws::realtime_ticket_handler),
        )
        // ── Production Routes ─────────────────────────────────────
        .route(
            "/api/v1/production/work-orders",
            get(routes::production::list_work_orders).post(routes::production::create_work_order),
        )
        .route(
            "/api/v1/production/work-orders/{id}",
            get(routes::production::get_work_order),
        )
        .route(
            "/api/v1/production/work-orders/{id}/status",
            put(routes::production::update_work_order_status),
        )
        .route(
            "/api/v1/production/work-orders/{id}/report",
            post(routes::production::report_production),
        )
        .route(
            "/api/v1/production/orders",
            get(routes::production::list_production_orders)
                .post(routes::production::create_production_order),
        )
        .route(
            "/api/v1/production/orders/{id}",
            get(routes::production::get_production_order),
        )
        .route(
            "/api/v1/production/orders/{id}/complete",
            post(routes::production::complete_production_order),
        )
        .route(
            "/api/v1/production/bom",
            post(routes::production::add_bom_item),
        )
        .route(
            "/api/v1/production/bom/{product_id}",
            get(routes::production::get_bom),
        )
        .route("/api/v1/production/mrp", post(routes::production::run_mrp))
        // ── Maintenance Routes ────────────────────────────────────
        .route(
            "/api/v1/maintenance/work-requests",
            get(routes::maintenance::list_work_requests)
                .post(routes::maintenance::create_work_request),
        )
        .route(
            "/api/v1/maintenance/work-requests/{id}",
            get(routes::maintenance::get_work_request)
                .put(routes::maintenance::update_work_request)
                .delete(routes::maintenance::delete_work_request),
        )
        .route(
            "/api/v1/maintenance/work-requests/{id}/status",
            put(routes::maintenance::update_work_request_status),
        )
        .route(
            "/api/v1/maintenance/work-requests/{id}/assign",
            post(routes::maintenance::assign_work_request),
        )
        .route(
            "/api/v1/maintenance/pm-schedules",
            get(routes::maintenance::list_pm_schedules)
                .post(routes::maintenance::create_pm_schedule),
        )
        .route(
            "/api/v1/maintenance/pm-schedules/{id}",
            get(routes::maintenance::get_pm_schedule)
                .put(routes::maintenance::update_pm_schedule)
                .delete(routes::maintenance::delete_pm_schedule),
        )
        .route(
            "/api/v1/maintenance/pm-schedules/{id}/complete",
            post(routes::maintenance::complete_pm_task),
        )
        .route(
            "/api/v1/maintenance/pm-schedules/overdue",
            get(routes::maintenance::get_overdue_pm_tasks),
        )
        .route(
            "/api/v1/maintenance/equipment",
            get(routes::maintenance::list_equipment).post(routes::maintenance::register_equipment),
        )
        .route(
            "/api/v1/maintenance/equipment/{id}",
            get(routes::maintenance::get_equipment)
                .put(routes::maintenance::update_equipment)
                .delete(routes::maintenance::delete_equipment),
        )
        .route(
            "/api/v1/maintenance/equipment/{id}/status",
            put(routes::maintenance::update_equipment_status),
        )
        // ── Finance Routes ────────────────────────────────────────
        .route(
            "/api/v1/finance/invoices",
            get(routes::finance::list_invoices).post(routes::finance::create_invoice),
        )
        .route(
            "/api/v1/finance/invoices/{id}",
            get(routes::finance::get_invoice)
                .put(routes::finance::update_invoice)
                .delete(routes::finance::delete_invoice),
        )
        .route(
            "/api/v1/finance/invoices/{id}/paid",
            post(routes::finance::mark_invoice_paid),
        )
        .route(
            "/api/v1/finance/payments",
            get(routes::finance::list_payments).post(routes::finance::record_payment),
        )
        .route(
            "/api/v1/finance/payments/{id}",
            put(routes::finance::update_payment).delete(routes::finance::delete_payment),
        )
        .route(
            "/api/v1/finance/budgets",
            get(routes::finance::list_budgets).post(routes::finance::create_budget),
        )
        .route(
            "/api/v1/finance/budgets/{id}",
            get(routes::finance::get_budget)
                .put(routes::finance::update_budget)
                .delete(routes::finance::delete_budget),
        )
        .route(
            "/api/v1/finance/budgets/{id}/allocate",
            post(routes::finance::allocate_budget),
        )
        .route(
            "/api/v1/finance/journal-entries",
            get(routes::finance::list_journal_entries).post(routes::finance::post_journal_entry),
        )
        .route(
            "/api/v1/finance/journal-entries/{id}",
            put(routes::finance::update_journal_entry)
                .delete(routes::finance::delete_journal_entry),
        )
        .route(
            "/api/v1/finance/journal-entries/{id}/reverse",
            post(routes::finance::reverse_journal_entry),
        )
        .route(
            "/api/v1/finance/cost-rollup",
            post(routes::finance::run_cost_rollup),
        )
        .route(
            "/api/v1/finance/cost-rollup/{product_id}",
            get(routes::finance::get_cost_rollup),
        )
        .route(
            "/api/v1/finance/three-way-match",
            post(routes::finance::match_three_way),
        )
        // ── HR Routes ─────────────────────────────────────────────
        .route(
            "/api/v1/hr/employees",
            get(routes::hr::list_employees).post(routes::hr::create_employee),
        )
        .route(
            "/api/v1/hr/employees/{id}",
            get(routes::hr::get_employee)
                .put(routes::hr::update_employee)
                .delete(routes::hr::delete_employee),
        )
        .route(
            "/api/v1/hr/employees/{id}/status",
            put(routes::hr::update_employee_status),
        )
        .route(
            "/api/v1/hr/training",
            get(routes::hr::list_training_records).post(routes::hr::record_training),
        )
        .route(
            "/api/v1/hr/training/expired",
            get(routes::hr::get_expired_certifications),
        )
        .route(
            "/api/v1/hr/training/{id}",
            put(routes::hr::update_training).delete(routes::hr::delete_training),
        )
        .route(
            "/api/v1/hr/leave",
            get(routes::hr::list_leave_requests).post(routes::hr::submit_leave_request),
        )
        .route(
            "/api/v1/hr/leave/{id}",
            put(routes::hr::update_leave).delete(routes::hr::delete_leave),
        )
        .route(
            "/api/v1/hr/leave/{id}/approve",
            post(routes::hr::approve_leave),
        )
        .route(
            "/api/v1/hr/leave/{id}/reject",
            post(routes::hr::reject_leave),
        )
        .route(
            "/api/v1/hr/reviews",
            get(routes::hr::list_reviews).post(routes::hr::create_review),
        )
        .route(
            "/api/v1/hr/reviews/{id}",
            put(routes::hr::update_review).delete(routes::hr::delete_review),
        )
        .route(
            "/api/v1/hr/reviews/{id}/complete",
            post(routes::hr::complete_review),
        )
        .route("/api/v1/hr/timecards", get(routes::hr::list_timecards))
        .route(
            "/api/v1/hr/timecards/{id}",
            put(routes::hr::update_timecard),
        )
        .route("/api/v1/hr/timecards/clock-in", post(routes::hr::clock_in))
        .route(
            "/api/v1/hr/timecards/clock-out",
            post(routes::hr::clock_out),
        )
        // ── Supply Chain Routes ───────────────────────────────────
        .route(
            "/api/v1/supply-chain/rfqs",
            get(routes::supply_chain::list_rfqs).post(routes::supply_chain::create_rfq),
        )
        .route(
            "/api/v1/supply-chain/rfqs/{id}",
            get(routes::supply_chain::get_rfq)
                .put(routes::supply_chain::update_rfq)
                .delete(routes::supply_chain::delete_rfq),
        )
        .route(
            "/api/v1/supply-chain/rfqs/{id}/status",
            put(routes::supply_chain::update_rfq_status),
        )
        .route(
            "/api/v1/supply-chain/rfqs/{id}/submit",
            post(routes::supply_chain::submit_rfq),
        )
        .route(
            "/api/v1/supply-chain/rfqs/{id}/cancel",
            post(routes::supply_chain::cancel_rfq),
        )
        .route(
            "/api/v1/supply-chain/quotes",
            get(routes::supply_chain::list_quotes).post(routes::supply_chain::create_quote),
        )
        .route(
            "/api/v1/supply-chain/quotes/{id}",
            get(routes::supply_chain::get_quote)
                .put(routes::supply_chain::update_quote)
                .delete(routes::supply_chain::delete_quote),
        )
        .route(
            "/api/v1/supply-chain/quotes/{id}/approve",
            post(routes::supply_chain::approve_quote),
        )
        .route(
            "/api/v1/supply-chain/quotes/{id}/submit",
            post(routes::supply_chain::submit_quote),
        )
        .route(
            "/api/v1/supply-chain/quotes/{id}/accept",
            post(routes::supply_chain::accept_quote),
        )
        .route(
            "/api/v1/supply-chain/quotes/{id}/reject",
            post(routes::supply_chain::reject_quote),
        )
        .route(
            "/api/v1/supply-chain/quotes/convert",
            post(routes::supply_chain::convert_quote_to_order),
        )
        .route(
            "/api/v1/supply-chain/sales-orders",
            get(routes::supply_chain::list_sales_orders)
                .post(routes::supply_chain::create_sales_order),
        )
        .route(
            "/api/v1/supply-chain/sales-orders/{id}",
            get(routes::supply_chain::get_sales_order)
                .put(routes::supply_chain::update_sales_order)
                .delete(routes::supply_chain::delete_sales_order),
        )
        .route(
            "/api/v1/supply-chain/sales-orders/{id}/status",
            put(routes::supply_chain::update_sales_order_status),
        )
        .route(
            "/api/v1/supply-chain/purchase-orders",
            get(routes::supply_chain::list_purchase_orders)
                .post(routes::supply_chain::create_purchase_order),
        )
        .route(
            "/api/v1/supply-chain/purchase-orders/{id}",
            get(routes::supply_chain::get_purchase_order)
                .put(routes::supply_chain::update_purchase_order)
                .delete(routes::supply_chain::delete_purchase_order),
        )
        .route(
            "/api/v1/supply-chain/purchase-orders/{id}/receive",
            post(routes::supply_chain::receive_po_line),
        )
        .route(
            "/api/v1/supply-chain/purchase-orders/{id}/receive-full",
            post(routes::supply_chain::receive_full_po),
        )
        .route(
            "/api/v1/supply-chain/inventory",
            get(routes::supply_chain::list_inventory),
        )
        .route(
            "/api/v1/supply-chain/inventory/{id}",
            get(routes::supply_chain::get_inventory)
                .put(routes::supply_chain::update_inventory)
                .delete(routes::supply_chain::delete_inventory),
        )
        .route(
            "/api/v1/supply-chain/inventory/adjust",
            post(routes::supply_chain::adjust_inventory),
        )
        .route(
            "/api/v1/supply-chain/stock-moves",
            get(routes::supply_chain::list_stock_moves)
                .post(routes::supply_chain::create_stock_move),
        )
        .route(
            "/api/v1/supply-chain/stock-moves/{id}",
            delete(routes::supply_chain::delete_stock_move),
        )
        // ── Operations Routes ─────────────────────────────────────
        .route(
            "/api/v1/ops/andons",
            get(routes::ops::list_andons).post(routes::ops::raise_andon),
        )
        .route(
            "/api/v1/ops/andons/{id}",
            get(routes::ops::get_andon)
                .put(routes::ops::update_andon)
                .delete(routes::ops::delete_andon),
        )
        .route(
            "/api/v1/ops/andons/{id}/acknowledge",
            post(routes::ops::acknowledge_andon),
        )
        .route(
            "/api/v1/ops/andons/{id}/resolve",
            post(routes::ops::resolve_andon),
        )
        .route(
            "/api/v1/ops/projects",
            get(routes::ops::list_projects).post(routes::ops::create_project),
        )
        .route(
            "/api/v1/ops/projects/{id}",
            get(routes::ops::get_project)
                .put(routes::ops::update_project)
                .delete(routes::ops::delete_project),
        )
        .route(
            "/api/v1/ops/projects/{id}/complete",
            post(routes::ops::complete_project),
        )
        .route(
            "/api/v1/ops/a3s",
            get(routes::ops::list_a3s).post(routes::ops::create_a3),
        )
        .route(
            "/api/v1/ops/a3s/{id}",
            get(routes::ops::get_a3)
                .put(routes::ops::update_a3)
                .delete(routes::ops::delete_a3),
        )
        .route("/api/v1/ops/a3s/{id}/close", post(routes::ops::close_a3))
        .route(
            "/api/v1/ops/risks",
            get(routes::ops::list_risks).post(routes::ops::create_risk),
        )
        .route(
            "/api/v1/ops/risks/{id}",
            get(routes::ops::get_risk)
                .put(routes::ops::update_risk)
                .delete(routes::ops::delete_risk),
        )
        .route(
            "/api/v1/ops/risks/{id}/mitigate",
            post(routes::ops::mitigate_risk),
        )
        // ── Quality Routes ────────────────────────────────────────
        .route(
            "/api/v1/quality/ncrs",
            get(routes::quality::list_ncrs).post(routes::quality::create_ncr),
        )
        .route(
            "/api/v1/quality/ncrs/{id}",
            get(routes::quality::get_ncr)
                .put(routes::quality::update_ncr)
                .delete(routes::quality::delete_ncr),
        )
        .route(
            "/api/v1/quality/ncrs/{id}/investigate",
            post(routes::quality::investigate_ncr),
        )
        .route(
            "/api/v1/quality/ncrs/{id}/disposition",
            post(routes::quality::disposition_ncr),
        )
        .route(
            "/api/v1/quality/ncrs/{id}/close",
            post(routes::quality::close_ncr),
        )
        .route(
            "/api/v1/quality/capas",
            get(routes::quality::list_capas).post(routes::quality::create_capa),
        )
        .route(
            "/api/v1/quality/capas/{id}",
            get(routes::quality::get_capa)
                .put(routes::quality::update_capa)
                .delete(routes::quality::delete_capa),
        )
        .route(
            "/api/v1/quality/capas/{id}/verify",
            post(routes::quality::verify_capa),
        )
        .route(
            "/api/v1/quality/capas/{id}/close",
            post(routes::quality::close_capa),
        )
        .route(
            "/api/v1/quality/audits",
            get(routes::quality::list_audits).post(routes::quality::create_audit),
        )
        .route(
            "/api/v1/quality/audits/{id}",
            get(routes::quality::get_audit)
                .put(routes::quality::update_audit)
                .delete(routes::quality::delete_audit),
        )
        .route(
            "/api/v1/quality/audits/{audit_id}/findings",
            get(routes::quality::list_audit_findings),
        )
        .route(
            "/api/v1/quality/supplier-scorecards",
            get(routes::quality::list_supplier_scorecards)
                .post(routes::quality::create_supplier_evaluation),
        )
        .route(
            "/api/v1/quality/supplier-scorecards/{id}",
            put(routes::quality::update_supplier_scorecard)
                .delete(routes::quality::delete_supplier_scorecard),
        )
        .route(
            "/api/v1/quality/scars",
            get(routes::quality::list_scars).post(routes::quality::create_scar),
        )
        .route(
            "/api/v1/quality/scars/{id}",
            get(routes::quality::get_scar)
                .put(routes::quality::update_scar)
                .delete(routes::quality::delete_scar),
        )
        .route(
            "/api/v1/quality/documents",
            get(routes::quality::list_documents).post(routes::quality::create_document),
        )
        .route(
            "/api/v1/quality/documents/{id}",
            get(routes::quality::get_document)
                .put(routes::quality::update_document)
                .delete(routes::quality::delete_document),
        )
        .route(
            "/api/v1/quality/first-article-inspections",
            get(routes::quality::list_first_article_inspections)
                .post(routes::quality::create_first_article_inspection),
        )
        .route(
            "/api/v1/quality/first-article-inspections/{id}",
            get(routes::quality::get_first_article_inspection)
                .put(routes::quality::update_first_article_inspection)
                .delete(routes::quality::delete_first_article_inspection),
        )
        .route(
            "/api/v1/quality/self-inspections",
            get(routes::quality::list_self_inspections)
                .post(routes::quality::create_self_inspection),
        )
        .route(
            "/api/v1/quality/self-inspections/{id}",
            get(routes::quality::get_self_inspection)
                .put(routes::quality::update_self_inspection)
                .delete(routes::quality::delete_self_inspection),
        )
        .route(
            "/api/v1/quality/msa-studies",
            get(routes::quality::list_msa_studies).post(routes::quality::create_msa_study),
        )
        .route(
            "/api/v1/quality/msa-studies/{id}",
            get(routes::quality::get_msa_study).delete(routes::quality::delete_msa_study),
        )
        .route(
            "/api/v1/quality/process-capability-studies",
            get(routes::quality::list_process_capability_studies)
                .post(routes::quality::create_process_capability_study),
        )
        .route(
            "/api/v1/quality/process-capability-studies/{id}",
            get(routes::quality::get_process_capability_study)
                .delete(routes::quality::delete_process_capability_study),
        )
        .route(
            "/api/v1/quality/control-plans",
            get(routes::quality::list_control_plans).post(routes::quality::create_control_plan),
        )
        .route(
            "/api/v1/quality/control-plans/{id}",
            get(routes::quality::get_control_plan)
                .put(routes::quality::update_control_plan)
                .delete(routes::quality::delete_control_plan),
        )
        .route(
            "/api/v1/quality/pfmeas",
            get(routes::quality::list_pfmeas).post(routes::quality::create_pfmea),
        )
        .route(
            "/api/v1/quality/pfmeas/{id}",
            get(routes::quality::get_pfmea).delete(routes::quality::delete_pfmea),
        )
        .route(
            "/api/v1/quality/npi-projects",
            get(routes::quality::list_npi_projects).post(routes::quality::create_npi_project),
        )
        .route(
            "/api/v1/quality/npi-projects/{id}",
            put(routes::quality::update_npi_project).delete(routes::quality::delete_npi_project),
        )
        .route(
            "/api/v1/quality/npi-projects/{project_id}/risks",
            get(routes::quality::list_npi_risks),
        )
        .route(
            "/api/v1/quality/gauges",
            get(routes::quality::list_gauges).post(routes::quality::create_gauge),
        )
        .route(
            "/api/v1/quality/gauges/{id}",
            get(routes::quality::get_gauge)
                .put(routes::quality::update_gauge)
                .delete(routes::quality::delete_gauge),
        )
        .route(
            "/api/v1/quality/complaints",
            get(routes::quality::list_complaints).post(routes::quality::create_complaint),
        )
        .route(
            "/api/v1/quality/complaints/{id}",
            get(routes::quality::get_complaint)
                .put(routes::quality::update_complaint)
                .delete(routes::quality::delete_complaint),
        )
        .route(
            "/api/v1/quality/eight-d-reports",
            get(routes::quality::list_eight_d_reports).post(routes::quality::create_eight_d_report),
        )
        .route(
            "/api/v1/quality/eight-d-reports/{id}",
            get(routes::quality::get_eight_d_report)
                .put(routes::quality::update_eight_d_report)
                .delete(routes::quality::delete_eight_d_report),
        )
        .route(
            "/api/v1/quality/management-reviews",
            get(routes::quality::list_management_reviews)
                .post(routes::quality::create_management_review),
        )
        .route(
            "/api/v1/quality/management-reviews/{id}",
            get(routes::quality::get_management_review)
                .put(routes::quality::update_management_review)
                .delete(routes::quality::delete_management_review),
        )
        // ── Kanban Routes ────────────────────────────────────────────
        .route(
            "/api/v1/kanban/boards",
            get(routes::kanban::list_boards).post(routes::kanban::create_board),
        )
        .route(
            "/api/v1/kanban/boards/{id}",
            get(routes::kanban::get_board)
                .put(routes::kanban::update_board)
                .delete(routes::kanban::delete_board),
        )
        .route(
            "/api/v1/kanban/boards/{board_id}/columns",
            post(routes::kanban::add_column),
        )
        .route(
            "/api/v1/kanban/columns/{id}",
            put(routes::kanban::update_column).delete(routes::kanban::delete_column),
        )
        .route(
            "/api/v1/kanban/columns/{column_id}/cards",
            post(routes::kanban::add_card),
        )
        .route(
            "/api/v1/kanban/cards/{id}",
            put(routes::kanban::update_card).delete(routes::kanban::delete_card),
        )
        .route(
            "/api/v1/kanban/cards/{id}/move",
            put(routes::kanban::move_card),
        )
        .route(
            "/api/v1/kanban/metrics",
            get(routes::kanban::get_kanban_metrics),
        )
        // ── Search Routes ────────────────────────────────────────────
        .route("/api/v1/search", get(routes::search::search))
        // ── Notification Routes ──────────────────────────────────────
        .route(
            "/api/v1/notifications",
            get(routes::notifications::list_notifications),
        )
        .route(
            "/api/v1/notifications/unread-count",
            get(routes::notifications::unread_count),
        )
        .route(
            "/api/v1/notifications/{id}/read",
            post(routes::notifications::mark_notification_read),
        )
        .route(
            "/api/v1/notifications/read-all",
            post(routes::notifications::mark_all_read),
        )
        .route(
            "/api/v1/notifications/preferences",
            get(routes::notifications::get_preferences)
                .put(routes::notifications::update_preferences),
        )
        // ── Attachment Routes ────────────────────────────────────────
        .route(
            "/api/v1/attachments/upload",
            post(routes::attachments::upload_attachment),
        )
        .route(
            "/api/v1/attachments/{id}/download",
            get(routes::attachments::download_attachment),
        )
        .route(
            "/api/v1/attachments/{entity_type}/{entity_id}",
            get(routes::attachments::list_attachments),
        )
        .route(
            "/api/v1/attachments/{id}",
            delete(routes::attachments::delete_attachment),
        )
        // ── RFQ Routes ───────────────────────────────────────────────
        .route(
            "/api/v1/rfqs",
            get(routes::rfqs::list_rfqs).post(routes::rfqs::create_rfq),
        )
        .route(
            "/api/v1/rfqs/{id}",
            get(routes::rfqs::get_rfq)
                .put(routes::rfqs::update_rfq)
                .delete(routes::rfqs::delete_rfq),
        )
        .route(
            "/api/v1/rfqs/{rfq_id}/line-items",
            post(routes::rfqs::add_rfq_line_item),
        )
        .route(
            "/api/v1/rfqs/{rfq_id}/line-items/{item_id}",
            put(routes::rfqs::update_rfq_line_item),
        )
        // ── Quote Routes ─────────────────────────────────────────────
        .route(
            "/api/v1/quotes",
            get(routes::quotes::list_quotes).post(routes::quotes::create_quote),
        )
        .route(
            "/api/v1/quotes/{id}",
            get(routes::quotes::get_quote)
                .put(routes::quotes::update_quote)
                .delete(routes::quotes::delete_quote),
        )
        .route(
            "/api/v1/quotes/{quote_id}/versions",
            post(routes::quotes::create_quote_version).get(routes::quotes::list_quote_versions),
        )
        // ── Learning Routes ──────────────────────────────────────────
        .route(
            "/api/v1/learning/modules",
            get(routes::learning::list_modules).post(routes::learning::create_module),
        )
        .route(
            "/api/v1/learning/modules/{id}",
            get(routes::learning::get_module)
                .put(routes::learning::update_module)
                .delete(routes::learning::delete_module),
        )
        // ── Opportunity Routes ───────────────────────────────────────
        .route(
            "/api/v1/opportunities",
            get(routes::opportunities::list_opportunities)
                .post(routes::opportunities::create_opportunity),
        )
        .route(
            "/api/v1/opportunities/{id}",
            get(routes::opportunities::get_opportunity)
                .put(routes::opportunities::update_opportunity)
                .delete(routes::opportunities::delete_opportunity),
        )
        // ── Escalation Policy Routes ─────────────────────────────────
        .route(
            "/api/v1/escalation-policies",
            get(routes::escalation::list_policies).post(routes::escalation::create_policy),
        )
        .route(
            "/api/v1/escalation-policies/{id}",
            get(routes::escalation::get_policy)
                .put(routes::escalation::update_policy)
                .delete(routes::escalation::delete_policy),
        )
        // ── Training Matrix Routes ────────────────────────────────────
        .route(
            "/api/v1/training-matrix",
            get(routes::training_matrix::list_matrix_entries)
                .post(routes::training_matrix::create_matrix_entry),
        )
        .route(
            "/api/v1/training-matrix/{id}",
            put(routes::training_matrix::update_matrix_entry),
        )
        .route(
            "/api/v1/training-matrix/skill-gaps",
            get(routes::training_matrix::list_skill_gaps),
        )
        // ── Knowledge Pack Routes ─────────────────────────────────────
        .route(
            "/api/v1/export/{entity_type}",
            get(routes::export::export_entity),
        )
        .route(
            "/api/v1/knowledge-packs",
            get(routes::knowledge::list_packs).post(routes::knowledge::create_pack),
        )
        .route(
            "/api/v1/knowledge-packs/{id}",
            get(routes::knowledge::get_pack)
                .put(routes::knowledge::update_pack)
                .delete(routes::knowledge::delete_pack),
        )
        // ── Smart Ingestion Routes ────────────────────────────────────
        .route(
            "/api/v1/smart-ingestion/upload",
            post(routes::smart_ingestion::upload_document),
        )
        .route(
            "/api/v1/smart-ingestion/{id}/status",
            get(routes::smart_ingestion::get_ingestion_status),
        )
        .route(
            "/api/v1/smart-ingestion/history",
            get(routes::smart_ingestion::list_ingestion_history),
        )
        // ── Work Orders Routes ────────────────────────────────────────────
        .route(
            "/api/v1/work-orders",
            get(routes::work_orders::list_work_orders).post(routes::work_orders::create_work_order),
        )
        .route(
            "/api/v1/work-orders/{id}",
            get(routes::work_orders::get_work_order)
                .put(routes::work_orders::update_work_order)
                .delete(routes::work_orders::delete_work_order),
        )
        .route(
            "/api/v1/work-orders/{id}/status",
            put(routes::work_orders::update_work_order_status),
        )
        .route(
            "/api/v1/work-orders/{id}/operations",
            get(routes::work_orders::list_work_order_operations),
        )
        .route(
            "/api/v1/work-orders/stats",
            get(routes::work_orders::get_work_order_stats),
        )
        // ── Work Centers Routes ───────────────────────────────────────────
        .route(
            "/api/v1/work-centers",
            get(routes::work_centers::list_work_centers)
                .post(routes::work_centers::create_work_center),
        )
        .route(
            "/api/v1/work-centers/{id}",
            get(routes::work_centers::get_work_center)
                .put(routes::work_centers::update_work_center)
                .delete(routes::work_centers::deactivate_work_center),
        )
        .route(
            "/api/v1/work-centers/{id}/capacity",
            get(routes::work_centers::get_work_center_capacity),
        )
        .route(
            "/api/v1/work-centers/efficiency-report",
            get(routes::work_centers::get_efficiency_report),
        )
        // ── Andon Routes ──────────────────────────────────────────────────
        .route(
            "/api/v1/andon",
            get(routes::andon::list_andons).post(routes::andon::raise_andon),
        )
        .route(
            "/api/v1/andon/{id}",
            get(routes::andon::get_andon)
                .put(routes::andon::update_andon)
                .delete(routes::andon::delete_andon),
        )
        .route(
            "/api/v1/andon/{id}/acknowledge",
            post(routes::andon::acknowledge_andon),
        )
        .route(
            "/api/v1/andon/{id}/resolve",
            post(routes::andon::resolve_andon),
        )
        // ── A3 Routes ─────────────────────────────────────────────────────
        .route(
            "/api/v1/a3",
            get(routes::a3::list_a3s).post(routes::a3::create_a3),
        )
        .route(
            "/api/v1/a3/{id}",
            get(routes::a3::get_a3)
                .put(routes::a3::update_a3)
                .delete(routes::a3::delete_a3),
        )
        .route("/api/v1/a3/{id}/close", post(routes::a3::close_a3))
        // ── Obeya Routes ──────────────────────────────────────────────────
        .route(
            "/api/v1/obeya/boards",
            get(routes::obeya::list_boards).post(routes::obeya::create_board),
        )
        .route(
            "/api/v1/obeya/boards/{id}",
            get(routes::obeya::get_board)
                .put(routes::obeya::update_board)
                .delete(routes::obeya::delete_board),
        )
        .route(
            "/api/v1/obeya/boards/{board_id}/items",
            get(routes::obeya::list_board_items).post(routes::obeya::add_board_item),
        )
        .route(
            "/api/v1/obeya/boards/{board_id}/items/{item_id}",
            put(routes::obeya::update_board_item).delete(routes::obeya::delete_board_item),
        )
        // ── Risk Routes ───────────────────────────────────────────────────
        .route(
            "/api/v1/risk",
            get(routes::risk::list_risks).post(routes::risk::create_risk),
        )
        .route(
            "/api/v1/risk/{id}",
            get(routes::risk::get_risk)
                .put(routes::risk::update_risk)
                .delete(routes::risk::delete_risk),
        )
        .route(
            "/api/v1/risk/{id}/mitigate",
            post(routes::risk::mitigate_risk),
        )
        // ── Inventory Routes ─────────────────────────────────────────────
        .route(
            "/api/v1/inventory/items",
            get(routes::inventory::list_inventory_items)
                .post(routes::inventory::create_inventory_item),
        )
        .route(
            "/api/v1/inventory/items/{id}",
            get(routes::inventory::get_inventory_item)
                .put(routes::inventory::update_inventory_item),
        )
        .route(
            "/api/v1/inventory/moves",
            get(routes::inventory::list_stock_moves).post(routes::inventory::create_stock_move),
        )
        .route(
            "/api/v1/inventory/warehouses",
            get(routes::inventory::list_warehouses).post(routes::inventory::create_warehouse),
        )
        .route(
            "/api/v1/inventory/stats",
            get(routes::inventory::get_inventory_stats),
        )
        // ── MRP Routes ───────────────────────────────────────────────────
        .route(
            "/api/v1/mrp/demand",
            get(routes::mrp::list_demand).post(routes::mrp::create_demand),
        )
        .route("/api/v1/mrp/supply", get(routes::mrp::list_supply))
        .route("/api/v1/mrp/run", post(routes::mrp::run_mrp))
        .route("/api/v1/mrp/runs", get(routes::mrp::list_mrp_runs))
        .route("/api/v1/mrp/runs/{id}", get(routes::mrp::get_mrp_run))
        // ── Tasks Routes ─────────────────────────────────────────────────
        .route(
            "/api/v1/tasks",
            get(routes::tasks::list_tasks).post(routes::tasks::create_task),
        )
        .route(
            "/api/v1/tasks/{id}",
            get(routes::tasks::get_task)
                .put(routes::tasks::update_task)
                .delete(routes::tasks::delete_task),
        )
        .route(
            "/api/v1/tasks/{id}/status",
            put(routes::tasks::update_task_status),
        )
        .route("/api/v1/tasks/{id}/assign", put(routes::tasks::assign_task))
        .route("/api/v1/tasks/stats", get(routes::tasks::get_task_stats))
        // ── Audit Log Routes ─────────────────────────────────────────────
        .route(
            "/api/v1/audit-logs",
            get(routes::audit_logs::list_audit_logs),
        )
        .route(
            "/api/v1/audit-logs/{id}",
            get(routes::audit_logs::get_audit_log),
        )
        .route(
            "/api/v1/audit-logs/entity/{entity_type}/{entity_id}",
            get(routes::audit_logs::get_entity_audit_trail),
        )
        .route(
            "/api/v1/audit-logs/stats",
            get(routes::audit_logs::get_audit_log_stats),
        )
        // ── Production Cells Routes ──────────────────────────────────────
        .route(
            "/api/v1/production-cells",
            get(routes::production_cells::list_production_cells)
                .post(routes::production_cells::create_production_cell),
        )
        .route(
            "/api/v1/production-cells/{id}",
            get(routes::production_cells::get_production_cell)
                .put(routes::production_cells::update_production_cell),
        )
        .route(
            "/api/v1/production-cells/{id}/utilization",
            get(routes::production_cells::get_cell_utilization),
        )
        // ── Saved Views Routes ───────────────────────────────────────────
        .route(
            "/api/v1/saved-views",
            get(routes::saved_views::list_saved_views).post(routes::saved_views::create_saved_view),
        )
        .route(
            "/api/v1/saved-views/{id}",
            get(routes::saved_views::get_saved_view)
                .put(routes::saved_views::update_saved_view)
                .delete(routes::saved_views::delete_saved_view),
        )
        .route(
            "/api/v1/saved-views/{id}/share",
            post(routes::saved_views::share_saved_view),
        )
        // ── Quoting Helper Routes ────────────────────────────────────────
        .route(
            "/api/v1/quoting-helper/rfqs/{rfq_id}/workpackets/generate",
            post(routes::quoting_helper::generate_work_packets),
        )
        .route(
            "/api/v1/quoting-helper/rfqs/{rfq_id}/workpackets",
            get(routes::quoting_helper::list_work_packets),
        )
        .route(
            "/api/v1/quoting-helper/workpackets/{packet_id}",
            patch(routes::quoting_helper::update_work_packet),
        )
        .route(
            "/api/v1/quoting-helper/rfqs/{rfq_id}/ingest",
            post(routes::quoting_helper::ingest_rfq_documents),
        )
        .route(
            "/api/v1/quoting-helper/quotes/{quote_id}/cost/build",
            post(routes::quoting_helper::build_quote_cost),
        )
        .route(
            "/api/v1/quoting-helper/quotes/{quote_id}/convert-to-npi",
            post(routes::quoting_helper::convert_quote_to_npi),
        )
        .route(
            "/api/v1/quoting-helper/ai/clarifications/suggest/{rfq_id}",
            get(routes::quoting_helper::suggest_clarifications),
        )
        .route(
            "/api/v1/quoting-helper/ai/quote-memory/retrieve/{rfq_id}",
            get(routes::quoting_helper::retrieve_quote_memory),
        )
        // ── Admin Routes ─────────────────────────────────────────────────
        .route(
            "/api/v1/admin/system-health",
            get(routes::admin::get_system_health),
        )
        .route("/api/v1/admin/db-stats", get(routes::admin::get_db_stats))
        .route("/api/v1/admin/users", get(routes::admin::admin_list_users))
        .route(
            "/api/v1/admin/users/{id}/deactivate",
            post(routes::admin::deactivate_user),
        )
        .route("/api/v1/admin/logs", get(routes::admin::get_system_logs))
        .route(
            "/api/v1/admin/config",
            get(routes::admin::get_system_config),
        )
        // ── CTQ Routes ────────────────────────────────────────────────────
        .route(
            "/api/v1/ctq/characteristics",
            get(routes::ctq::list_characteristics).post(routes::ctq::create_characteristic),
        )
        .route(
            "/api/v1/ctq/characteristics/{id}",
            get(routes::ctq::get_characteristic).put(routes::ctq::update_characteristic),
        )
        .route(
            "/api/v1/ctq/characteristics/{id}/records",
            get(routes::ctq::list_records).post(routes::ctq::create_record),
        )
        .route(
            "/api/v1/ctq/characteristics/{id}/analysis",
            get(routes::ctq::get_conformance_analysis),
        )
        // ── KPI Routes ────────────────────────────────────────────────────
        .route(
            "/api/v1/kpi",
            get(routes::kpi::list_kpis).post(routes::kpi::create_kpi),
        )
        .route(
            "/api/v1/kpi/{kpi_id}",
            get(routes::kpi::get_kpi)
                .put(routes::kpi::update_kpi)
                .delete(routes::kpi::delete_kpi),
        )
        .route(
            "/api/v1/kpi/{kpi_id}/values",
            get(routes::kpi::list_kpi_values).post(routes::kpi::record_kpi_value),
        )
        .route(
            "/api/v1/kpi/{kpi_id}/dashboard",
            get(routes::kpi::get_kpi_dashboard),
        )
        // ── LSW Routes ────────────────────────────────────────────────────
        .route(
            "/api/v1/lsw/standards",
            get(routes::lsw::list_lsw_standards).post(routes::lsw::create_lsw_standard),
        )
        .route(
            "/api/v1/lsw/standards/{standard_id}",
            get(routes::lsw::get_lsw_standard)
                .put(routes::lsw::update_lsw_standard)
                .delete(routes::lsw::delete_lsw_standard),
        )
        .route(
            "/api/v1/lsw/standards/{standard_id}/audits",
            get(routes::lsw::list_audits).post(routes::lsw::perform_audit),
        )
        .route("/api/v1/lsw/audits/{audit_id}", get(routes::lsw::get_audit))
        .route("/api/v1/lsw/dashboard", get(routes::lsw::get_lsw_dashboard))
        // ── Notification Trigger Routes ────────────────────────────────────
        .route(
            "/api/v1/notification-triggers",
            get(routes::notification_triggers::list_triggers)
                .post(routes::notification_triggers::create_trigger),
        )
        .route(
            "/api/v1/notification-triggers/{trigger_id}",
            get(routes::notification_triggers::get_trigger)
                .put(routes::notification_triggers::update_trigger)
                .delete(routes::notification_triggers::delete_trigger),
        )
        .route(
            "/api/v1/notification-triggers/{trigger_id}/toggle",
            patch(routes::notification_triggers::toggle_trigger),
        )
        .route(
            "/api/v1/notification-triggers/{trigger_id}/test",
            post(routes::notification_triggers::test_trigger),
        )
        .route(
            "/api/v1/notification-triggers/event-types",
            get(routes::notification_triggers::list_event_types),
        )
        // ── Standard Work Routes ───────────────────────────────────────────
        .route(
            "/api/v1/standard-work",
            get(routes::standard_work::list_standard_work)
                .post(routes::standard_work::create_standard_work),
        )
        .route(
            "/api/v1/standard-work/{sw_id}",
            get(routes::standard_work::get_standard_work)
                .put(routes::standard_work::update_standard_work)
                .delete(routes::standard_work::delete_standard_work),
        )
        .route(
            "/api/v1/standard-work/{sw_id}/versions",
            get(routes::standard_work::list_versions).post(routes::standard_work::create_version),
        )
        .route(
            "/api/v1/standard-work/{sw_id}/versions/{version_id}",
            get(routes::standard_work::get_version),
        )
        // ── State Machine Routes ───────────────────────────────────────────
        .route(
            "/api/v1/state-machines",
            get(routes::state_machines::list_state_machines)
                .post(routes::state_machines::create_state_machine),
        )
        .route(
            "/api/v1/state-machines/{sm_id}",
            get(routes::state_machines::get_state_machine)
                .put(routes::state_machines::update_state_machine)
                .delete(routes::state_machines::delete_state_machine),
        )
        .route(
            "/api/v1/state-machines/{sm_id}/instances",
            get(routes::state_machines::list_instances)
                .post(routes::state_machines::create_instance),
        )
        .route(
            "/api/v1/state-machines/instances/{instance_id}",
            get(routes::state_machines::get_instance),
        )
        .route(
            "/api/v1/state-machines/instances/{instance_id}/transition",
            post(routes::state_machines::transition_instance),
        )
        // ── Training Routes ────────────────────────────────────────────────
        .route(
            "/api/v1/training/courses",
            get(routes::training::list_courses).post(routes::training::create_course),
        )
        .route(
            "/api/v1/training/courses/{course_id}",
            get(routes::training::get_course)
                .put(routes::training::update_course)
                .delete(routes::training::delete_course),
        )
        .route(
            "/api/v1/training/courses/{course_id}/enroll",
            post(routes::training::enroll_users),
        )
        .route(
            "/api/v1/training/courses/{course_id}/enrollments",
            get(routes::training::list_enrollments),
        )
        .route(
            "/api/v1/training/enrollments/{enrollment_id}",
            patch(routes::training::update_enrollment_status),
        )
        .route(
            "/api/v1/training/my-courses",
            get(routes::training::my_courses),
        )
        .route(
            "/api/v1/training/dashboard",
            get(routes::training::get_training_dashboard),
        )
        // ── Today Routes ──────────────────────────────────────────────────
        .route("/api/v1/today", get(routes::today::get_today_snapshot))
        // ── Protected-route middleware layers ─────────────────────────────
        // route_layer is applied bottom-to-top too: the LAST layer added
        // runs FIRST (outermost). Layers are therefore added innermost-first
        // so the execution order is:
        //   auth → session → idempotency → audit → handler
        // - audit is innermost (added first): it runs after auth, so it can
        //   read AuthenticatedUser, and it times the handler itself.
        // - idempotency runs after auth (user-scoped cache keys).
        // - session binding runs after auth (fingerprint checks).
        // - auth is outermost (added last).
        // Audit logging – record state-changing requests (innermost).
        .route_layer(middleware::from_fn_with_state(
            state.clone(),
            audit_middleware,
        ))
        // Idempotency – handle Idempotency-Key for POST/PUT/PATCH.
        .route_layer(middleware::from_fn({
            let store = Arc::clone(&idempotency_store);
            move |mut req: Request, next: Next| {
                req.extensions_mut().insert((*store).clone());
                async move { idempotency_middleware(req, next).await }
            }
        }))
        // Session binding – enforce fingerprint checks for authenticated users.
        .route_layer(middleware::from_fn_with_state(
            state.clone(),
            session_binding_middleware,
        ))
        // Authentication (outermost – runs first for the route handler).
        .route_layer(middleware::from_fn_with_state(state.clone(), auth_layer));

    // ── Determine static files directory ────────────────────────────
    // The Leptos/Trunk build output (Docker: /app/static via STATIC_DIR;
    // dev: the crate dist dir). The legacy HTML frontend was removed —
    // there is exactly ONE frontend now.
    let static_dir = std::env::var("SENSEI_STATIC_DIR")
        .or_else(|_| std::env::var("STATIC_DIR"))
        .unwrap_or_else(|_| "crates/sensei-frontend/dist".to_string());

    // ── Protected streaming routes (auth required, NO timeout) ──────
    // `chat_stream` is a long-lived SSE stream: like the real-time routes
    // it must not be wrapped in the request timeout, but it is still
    // authenticated with the same protected-route stack.
    let protected_streaming_routes = Router::new()
        .route("/api/v1/chat/stream", post(routes::chatbot::chat_stream))
        // Audit logging – record state-changing requests (innermost).
        .route_layer(middleware::from_fn_with_state(
            state.clone(),
            audit_middleware,
        ))
        // Idempotency – handle Idempotency-Key for POST/PUT/PATCH.
        .route_layer(middleware::from_fn({
            let store = Arc::clone(&idempotency_store);
            move |mut req: Request, next: Next| {
                req.extensions_mut().insert((*store).clone());
                async move { idempotency_middleware(req, next).await }
            }
        }))
        // Session binding – enforce fingerprint checks for authenticated users.
        .route_layer(middleware::from_fn_with_state(
            state.clone(),
            session_binding_middleware,
        ))
        // Authentication (outermost – runs first for the route handler).
        .route_layer(middleware::from_fn_with_state(state.clone(), auth_layer));

    // ── Timeout-scoped routes (everything non-streaming) ───────────
    // The single global request timeout (Timeout is 408 via
    // TimeoutLayer::with_status_code) wraps ONLY this nested router so
    // long-lived WS/SSE connections are never killed by it.
    let timed_routes = Router::new()
        .route("/", get(root_handler))
        .merge(public_routes)
        .merge(protected_streaming_routes)
        .merge(protected_routes)
        // ── Unmatched /api/* paths → structured JSON 404 ────────────
        // Registered before the ServeDir fallback so API 404s never fall
        // through to the static frontend.
        .route("/api/{*rest}", get(api_not_found))
        .layer(TimeoutLayer::with_status_code(
            axum::http::StatusCode::REQUEST_TIMEOUT,
            Duration::from_secs(state.config.api.request_timeout_secs),
        ));

    // ── Merge and apply global layers ───────────────────────────────
    // Layers are applied bottom-to-top; the LAST layer added runs FIRST
    // (outermost). The execution order is documented at the top of this
    // file. The critical invariant for rate limiting is that
    // `inject_rate_limiter` is OUTER to `rate_limit_middleware` (added
    // after it) so the limiter always finds its instance.
    Router::new()
        .merge(realtime_routes)
        .merge(timed_routes)
        // ── Serve WASM frontend static files as fallback ────────────
        .fallback_service(ServeDir::new(static_dir))
        .layer(CompressionLayer::new())
        // ── Request body limit (streams, so chunked bodies are covered) ──
        .layer(RequestBodyLimitLayer::new(
            request_guard_config.max_body_size,
        ))
        // ── Request guard – method restrictions only ─────────────────
        .layer(middleware::from_fn({
            let guard = Arc::clone(&request_guard_config);
            move |mut req: Request, next: Next| {
                req.extensions_mut().insert((*guard).clone());
                async move { request_guard_middleware(req, next).await }
            }
        }))
        // ── Rate limiting – consumer first, then injector (outer) ───
        .layer(middleware::from_fn(rate_limit_middleware))
        .layer(middleware::from_fn_with_state(
            state.clone(),
            inject_rate_limiter,
        ))
        // ── Metrics collection ───────────────────────────────────────
        .layer(middleware::from_fn(metrics_middleware))
        // ── Request identification & logging ─────────────────────────
        .layer(TraceLayer::new_for_http())
        .layer(middleware::from_fn(logging_middleware))
        .layer(middleware::from_fn(request_id_middleware))
        // ── CORS & security headers (outermost) ──────────────────────
        .layer(cors_layer)
        .layer(middleware::from_fn_with_state(
            state.clone(),
            secure_headers_middleware,
        ))
        .with_state(state)
}
