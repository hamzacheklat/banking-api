import datetime

vanish_flw_collection = FlowsCollection()

def get_recurrent_task_failed_flow(last_n_days: int, top_n: int, **kwargs):
    vanish_flw_collection: FlowsCollection = vanish_flw_collection(**kwargs)

    # 1- group the jobs by flow_name and task that causes its failure
    # 2- count the number of occurrences of each task

    kwargs_updated = {"status": kwargs.get("status", "").upper()}
    filter_by = {k: v for (k, v) in kwargs.items() if v}
    down_date, up_date = get_down_up_date(last_n_days)

    pipeline = [
        {"$match": {
            **filter_by,
            "start_time": {"$lte": datetime.fromisoformat(up_date), "$gt": datetime.fromisoformat(down_date)},
            "status": "FAILED"
        }},
        {"$group": {
            "_id": {
                "flow_name": "$flow_name",
                "name_task_failed": "$name_task_failed"
            },
            "techno": {"$first": "$techno"},
            "task_failed_issue_by": {"$first": "$task_failed_issue_by"},
            "number_of_failure": {"$sum": 1}
        }},
        {"$sort": {"number_of_failure": -1}},
        {"$limit": top_n}
    ]

    group_task_cause_fail = list(vanish_flw_collection.generic_flow_collection_request(pipeline=pipeline))

    if group_task_cause_fail:
        pipeline = [
            {"$match": {
                **filter_by,
                "start_time": {"$lte": datetime.fromisoformat(up_date), "$gt": datetime.fromisoformat(down_date)},
                "status": {"$in": ["FAILED", "SUCCESS"]}
            }},
            {"$group": {
                "_id": {
                    "flow_name": "$flow_name",
                    "name_task_failed": "$name_task_failed"
                },
                "total_successes": {"$sum": {"$cond": [{"$eq": ["$status", "SUCCESS"]}, 1, 0]}},
                "total_failures": {"$sum": {"$cond": [{"$eq": ["$status", "FAILED"]}, 1, 0]}}
            }},
            {"$project": {
                "success_rate": {
                    "$round": [
                        {"$multiply": [
                            {"$divide": ["$total_successes", {"$add": ["$total_successes", "$total_failures"]}]},
                            100
                        ]},
                        2
                    ]
                },
                "failed_rate": {
                    "$round": [
                        {"$multiply": [
                            {"$divide": ["$total_failures", {"$add": ["$total_successes", "$total_failures"]}]},
                            100
                        ]},
                        2
                    ]
                }
            }}
        ]

        success_fail_rate_by_flow = {
            (k['_id']['flow_name'], k['_id']['name_task_failed']): {
                'failed_rate': k['failed_rate'],
                'success_rate': k['success_rate']
            }
            for k in list(vanish_flw_collection.generic_flow_collection_request(pipeline=pipeline))
        }

        for element in group_task_cause_fail:
            key = (element['_id']['flow_name'], element['_id']['name_task_failed'])
            element.update(success_fail_rate_by_flow.get(key, {'failed_rate': 0, 'success_rate': 0}))

    return group_task_cause_fail
