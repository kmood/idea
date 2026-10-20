"""Default bounds for an Agent-coordinated research run."""
from datetime import datetime, timezone

DEFAULT_LIMITS = dict(searches=12,candidates=10,auxiliary=8,total=40)


def new_request(source_ids, queries, current_time, limits=None):
    return dict(sourceIds=source_ids,queries=queries,
                limits=dict(DEFAULT_LIMITS) if limits is None else limits,
                deadline=datetime.fromtimestamp(current_time+1200,timezone.utc).isoformat())


def validate_draft(draft):
    from records.contracts import fields,require,text,string_list
    keys=set('candidateId disposition reason nextCondition claims unknowns counterEvidence target content'.split())
    fields(draft,keys,keys)
    require(text(draft['candidateId']) and text(draft['reason']))
    require(draft['disposition'] in ('trend','idea','update','deferred','rejected'))
    require(draft['nextCondition'] is None or text(draft['nextCondition']))
    require(string_list(draft['unknowns']) and len(draft['unknowns'])<=100)
    require(isinstance(draft['claims'],list) and len(draft['claims'])<=100)
    require(isinstance(draft['counterEvidence'],list) and len(draft['counterEvidence'])<=100)
    if draft['disposition'] in ('deferred','rejected'):
        require(draft['content'] is None and draft['target'] is None and text(draft['nextCondition']))
    elif draft['disposition']=='update':
        from records.artifacts import ref
        ref(draft['target']);fields(draft['content'],{'summary'},{'summary'});require(text(draft['content']['summary']))
    else:
        require(draft['target'] is None)
        if draft['disposition']=='trend':
            keys={'title','summary','impact','questions'};fields(draft['content'],keys,keys)
            require(all(text(draft['content'][k]) for k in ('title','summary')))
            require(string_list(draft['content']['questions']))
            impact=draft['content']['impact'];fields(impact,{'nature','text'},{'nature','text'})
            require(impact['nature'] in ('fact','author_claim','inference') and text(impact['text']))
        else:
            keys={'title','audience','problem','earningHypothesis','industry','sideHustleTypes','markets','cost'}
            fields(draft['content'],keys,keys)
            require(all(text(draft['content'][k]) for k in ('title','audience','problem','earningHypothesis')))
            require(all(string_list(draft['content'][k]) and draft['content'][k] for k in ('industry','sideHustleTypes','markets')))
            require(draft['content']['cost'] is None or text(draft['content']['cost']))
    if draft['disposition']!='deferred':require(bool(draft['claims']),'Disposition requires read claims')
