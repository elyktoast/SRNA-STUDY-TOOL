import {DurableObject} from 'cloudflare:workers';
export {McBatch} from '../src/mc-batch-object.js';

export class FakeReviewer extends DurableObject {
 async startAndWaitForPorts() {}
 async fetch(request) {
  const {request:slot,prior} = await request.json();
  if (slot.topic === 'disconnect' && !slot.resume_completed_only) return new Response(null,{status:503});
  const stages = Object.fromEntries(['schema','deterministic_text','math','evidence','duplicates','blind_model',
   'editorial_quality','explanation_evidence','independent_option_evidence','options_only'].map(name => [name,{status:'pass',issues:[]}]));
  if (slot.topic === 'provider outage') stages.independent_option_evidence = {status:'pending',provider_rule:'PROVIDER_UPSTREAM'};
  if (slot.topic === 'second' && prior.length !== 1) return new Response(null,{status:400});
  return Response.json({draft_id:slot.item_id,published:false,requires_human_review:true,
   draft_status:slot.topic === 'provider outage'?'needs_revision':'pending_review',screening:{stages}});
 }
}
export default {fetch:() => new Response(null,{status:404})};
