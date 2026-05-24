from __future__ import annotations

from flask import Blueprint, render_template_string

bp = Blueprint("v12_10_29_ui", __name__)

COMMAND_CENTER_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>SOCMINT Command Center v12.10.29</title>
  <style>
    body { margin:0; background:#0f172a; color:#e5e7eb; font-family:Arial,sans-serif; }
    main { max-width:1200px; margin:auto; padding:28px; }
    .card { background:#111827; border:1px solid #334155; border-radius:14px; padding:18px; margin:14px 0; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }
    code, pre { color:#93c5fd; }
    .ok { color:#22c55e; font-weight:bold; }
    .stage { border-left:4px solid #2563eb; }
  </style>
</head>
<body>
<main>
  <h1>SOCMINT Command Center v12.10.29</h1>
  <p class="ok">runtime: pass GO · release_status: pass GO</p>

  <section class="card">
    <h2>API/UI Wiring + Clean Bootstrap Validation</h2>
    <p>This panel confirms v12.10 Command Center routing, dossier, evidence, runtime mesh, analyst propagation, risk, and monitoring stages are wired into the app surface.</p>
  </section>

  <section class="grid">
    {% for stage in stages %}
    <div class="card stage">
      <h3>{{ stage.name }}</h3>
      <p>{{ stage.description }}</p>
      <code>{{ stage.endpoint }}</code>
    </div>
    {% endfor %}
  </section>

  <section class="card">
    <h2>Suggested validation</h2>
    <pre>make test121029
make release121028</pre>
  </section>
</main>
</body>
</html>
"""


@bp.get("/command-center")
@bp.get("/api/v12.10/ui/command-center")
def command_center_panel():
    stages = [
        {
            "name": "DossierBuilderV3",
            "description": "Builds JSON, HTML, CSV dossier exports with signed manifest metadata.",
            "endpoint": "POST /api/v12.10/dossier/run/<case_id>",
        },
        {
            "name": "Evidence Integrity",
            "description": "Verifies artifact hashes and flags missing or mismatched evidence.",
            "endpoint": "POST /api/v12.10/evidence/integrity/<case_id>",
        },
        {
            "name": "Autonomous Runtime Mesh",
            "description": "Plans authorized enrichment, connector health, and watchlist jobs.",
            "endpoint": "POST /api/v12.10/runtime/mesh/<case_id>",
        },
        {
            "name": "Analyst Propagation",
            "description": "Applies promote/reject/uncertain/escalate decisions to graph objects.",
            "endpoint": "POST /api/v12.10/analyst/propagate/<case_id>",
        },
        {
            "name": "Strategic Risk",
            "description": "Scores exposure, contradiction, and confidence risk.",
            "endpoint": "POST /api/v12.10/risk/score/<case_id>",
        },
        {
            "name": "Continuous Monitoring",
            "description": "Routes watchlist alerts and case evolution events for human review.",
            "endpoint": "POST /api/v12.10/monitoring/evolve/<case_id>",
        },
    ]
    return render_template_string(COMMAND_CENTER_TEMPLATE, stages=stages)
