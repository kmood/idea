"""Default bounds for an Agent-coordinated research run."""
from datetime import datetime, timezone

DEFAULT_LIMITS = dict(searches=12,candidates=10,auxiliary=8,total=40)


def new_request(source_ids, queries, current_time, limits=None):
    return dict(sourceIds=source_ids,queries=queries,
                limits=dict(DEFAULT_LIMITS) if limits is None else limits,
                deadline=datetime.fromtimestamp(current_time+1200,timezone.utc).isoformat())
