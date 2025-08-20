def register_cli(app):
    from .alerts import recalc_alerts_all
    @app.cli.command("alerts-recalc")
    def alerts_recalc():
        recalc_alerts_all()
        print("Alerts recalculated.")
