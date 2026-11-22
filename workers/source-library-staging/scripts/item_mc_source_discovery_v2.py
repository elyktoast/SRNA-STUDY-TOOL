"""Bounded search preparation, never clinical evidence or question approval."""
from build_question_evidence import _source_records, build_evidence, topic_search_query
from search_passages import search_many, supports_pipeline
from item_generation_checkpoint_store_v2 import fingerprint


def discover(conn, args, packet, planner):
    response = planner({'step':'retrieval_plan','rules_version':'2.0','auto_publish':False,
                        'format':'MC','topic':args.topic})
    if not isinstance(response,dict) or set(response) != {'focus_query','alternative_queries'}:
        raise ValueError('Invalid source search plan')
    alternatives=response['alternative_queries']
    if not isinstance(alternatives,list) or not 1 <= len(alternatives) <= 3:
        raise ValueError('Invalid source search plan')
    queries=[response['focus_query'],*alternatives]
    if (not isinstance(queries,list) or not 1 <= len(queries) <= 4
            or any(not isinstance(q,str) or not 2 <= len(q.strip()) <= 100 for q in queries)):
        raise ValueError('Invalid source search plan')
    queries=list(dict.fromkeys(' '.join(q.split()) for q in queries))
    if len(queries)<2: raise ValueError('Invalid source search plan')
    books=getattr(args,'textbook_ids',None) or [args.textbook_id]
    groups=[]
    if all(books) and len(queries) * len(books) <= 32 and all(" — " not in query for query in queries) and supports_pipeline(conn):
        scopes = [{"textbook_id": book, "limit": 2, "section_id": args.section_id,
                   "include_subsections": args.include_subsections, "page_start": args.page_start,
                   "page_end": args.page_end} for book in books]
        requests = [(topic_search_query(query), scope) for query in queries for scope in scopes]
        results = search_many(conn, args.owner_uid, requests)
        for i in range(0, len(results), len(books)):
            candidates = []
            for book, rows in zip(books, results[i:i + len(books)]):
                if any(row.get("textbook_id") != book for row in rows):
                    raise ValueError('Source discovery escaped selected textbooks')
                candidates.extend(_source_records(rows))
            groups.append(candidates)
    else:
        for query in queries:
            candidates=[]
            for book in books:
                result=build_evidence(conn,args.owner_uid,query,textbook_id=book,limit=2,
                    section_id=args.section_id,include_subsections=args.include_subsections,
                    page_start=args.page_start,page_end=args.page_end)
                if any(p.get('textbook_id') != book for p in result['sources']):
                    raise ValueError('Source discovery escaped selected textbooks')
                candidates.extend(result['sources'])
            groups.append(candidates)
    sources=list(packet['sources'])
    existing={p['passage_id'] for p in sources}
    added=[]
    # One previously unseen candidate per query before a second from any query.
    for index in range(max((len(group) for group in groups),default=0)):
        for group in groups:
            if index >= len(group): continue
            passage=group[index]
            if passage['passage_id'] in existing: continue
            if passage['textbook_id'] not in books:
                raise ValueError('Source discovery escaped selected textbooks')
            existing.add(passage['passage_id']);added.append(passage)
            if len(added)==4: break
        if len(added)==4: break
    sources.extend(added)
    return ({**packet,'sources':sources,'evidence_count':len(sources)},
            {'candidate_queries':queries,'passage_ids':[p['passage_id'] for p in added],
             'source_packet_sha256':fingerprint(added),'model_calls':1,'database_writes':False,
             'clinical_truth_verified':False})
