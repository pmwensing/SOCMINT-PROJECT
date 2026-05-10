from .dashboard import create_app
from .full_report_alias import register_full_report_aliases
from .full_report_browser import register_full_report_browser_flow
from .full_report_history import register_full_report_history_routes


app = create_app()
register_full_report_aliases(app)
register_full_report_browser_flow(app)
register_full_report_history_routes(app)
