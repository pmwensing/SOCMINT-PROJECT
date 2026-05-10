from .dashboard import create_app
from .full_report_alias import register_full_report_aliases


app = create_app()
register_full_report_aliases(app)
