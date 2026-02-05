def check_databases(self, treatment_name):
    overall_status = 200
    databases_response = {}

    for db_name in self.db_config:
        if db_name == "iv2":
            continue

        db_health = self.check(db_name, treatment_name)
        db_payload = db_health["response"]

        databases_response[db_name] = {
            "status": "Healthy" if db_health["status"] == 200 else "Unhealthy",
            "response_time": db_payload.get("response_time"),
        }

        if db_health["status"] != 200:
            overall_status = 503
            databases_response[db_name]["error"] = db_payload.get("error", "Unknown error")

    return {
        "response": {
            "databases": databases_response
        },
        "status": overall_status
    }
