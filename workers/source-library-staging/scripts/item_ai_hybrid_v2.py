"""Route staging question steps through independently configured model adapters."""

def make_hybrid_adapter(*, concept_adapter, draft_adapter, rationale_adapter):
    adapters = {'concept_card': concept_adapter, 'item_draft': draft_adapter, 'rationale': rationale_adapter}
    if not all(callable(adapter) for adapter in adapters.values()):
        raise ValueError('All hybrid adapters must be configured')
    def generate(request):
        step = request.get('step') if isinstance(request, dict) else None
        if step not in adapters:
            raise ValueError('Unsupported hybrid step')
        return adapters[step](request)
    return generate
