import {DurableObject} from 'cloudflare:workers';
export {McBatch} from '../src/mc-batch-object.js';

export class FakeReviewer extends DurableObject {
 async startAndWaitForPorts() {}
 async fetch(request) {
  const {request:slot,prior} = await request.json();
  if (slot.topic === 'busy once' && !slot.resume_completed_only && !await this.ctx.storage.get(slot.item_id)) {
   await this.ctx.storage.put(slot.item_id,true);
   return Response.json({rule:'GENERATION_BUSY'},{status:409});
  }
  if (slot.topic === 'explicit provider failure') {
   return slot.resume_completed_only
    ? Response.json({rule:'CHECKPOINT_NOT_COMPLETE'},{status:409})
    : Response.json({rule:'PROVIDER_RATE_LIMIT',retry_after_seconds:40},{status:429});
  }
  if (slot.topic === 'unconfirmed') return new Response(null,{status:503});
  if (slot.topic === 'disconnect' && !slot.resume_completed_only) return new Response(null,{status:503});
  const stages = Object.fromEntries(['schema','deterministic_text','math','evidence','duplicates','blind_model',
   'editorial_quality','explanation_evidence','independent_option_evidence','options_only'].map(name => [name,{status:'pass',issues:[]}]));
  if (slot.topic === 'provider outage') stages.independent_option_evidence = {status:'pending',issues:[{rule_id:'R-12.4'}]};
  if (slot.topic === 'second' && prior.length !== 1) return new Response(null,{status:400});
  return Response.json({draft_id:slot.item_id,published:false,requires_human_review:slot.topic === 'provider outage',
   draft_status:slot.topic === 'provider outage'?'needs_revision':'approved_for_bank',screening:{stages,...(slot.topic === 'provider outage' ? {independent_option_adjudication:{provider_rule:'PROVIDER_UPSTREAM'}} : {})}});
 }
}
export default {fetch:() => new Response(null,{status:404})};
