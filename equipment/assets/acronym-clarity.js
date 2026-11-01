/* Study Studio display-only acronym clarity.
   Keep common anesthesia abbreviations (PEEP, PIP, Pplat, BP, OR, etc.).
   Never mutate canonical questions, answer keys, saved attempts, or source citations. */
(function(root) {
  'use strict';
  const expansions = Object.freeze({
    AGS: 'alpha-gal syndrome',
    BJR: 'Bezold–Jarisch reflex',
    CICO: 'cannot intubate, cannot oxygenate',
    DISS: 'diameter index safety system',
    HME: 'heat and moisture exchanger',
    LAST: 'local anesthetic systemic toxicity',
    NMT: 'neuromuscular transmission',
    PISS: 'pin index safety system',
    RQ: 'respiratory quotient',
    SIRS: 'systemic inflammatory response syndrome',
    VAP: 'ventilator-associated pneumonia',
    VAE: 'ventilator-associated event',
    VILI: 'ventilator-induced lung injury',
    VQ: 'ventilation–perfusion ratio',
    Pmean: 'mean airway pressure',
    Raw: 'airway resistance',
    Ti: 'inspiratory time',
    Te: 'expiratory time',
  });
  const pattern = new RegExp('\\b(?:' + Object.keys(expansions).sort((a,b) => b.length-a.length).join('|') + ')\\b','g');
  const mechanical = Object.freeze({Pmean:'mean airway pressure',Raw:'airway resistance',Ti:'inspiratory time',Te:'expiratory time'});
  function clarify(text, options={}) {
    if (typeof text !== 'string' || !text) return text;
    if (/regional|neuraxial/i.test(String(options.topic||''))) return text;
    if (/respiratory|ventilat|airway mechanics/i.test(String(options.topic||''))) {
      text = text.replace(/\\bTV\\b/g, 'Vt').replace(/\\bVE\\b/g,'MV');
    }
    const introduced = new Set();
    let result=text.replace(pattern, (short, offset, whole) => {
      const meaning = expansions[short];
      if (introduced.has(short)) return short;
      introduced.add(short);
      // Avoid duplicating an expansion already directly present in the source text.
      const pre = whole.slice(Math.max(0,offset-meaning.length-6),offset).toLowerCase();
      const post = whole.slice(offset+short.length,offset+short.length+meaning.length+6).toLowerCase();
      if (pre.includes(meaning.toLowerCase()) || post.includes(meaning.toLowerCase())) return short;
      return meaning + ' (' + short + ')';
    });
    // If the full mechanics term is already present, introduce its symbol once.
    for (const [short, meaning] of Object.entries(mechanical)) {
      if (!text.includes(short) && result.toLowerCase().includes(meaning)) {
        const re=new RegExp('\\\\b'+meaning.replace(/ /g,'\\\\s+')+'\\\\b','i');
        result=result.replace(re, m => m+' ('+short+')');
      }
    }
    return result;
  }
  const api=Object.freeze({clarify,expansions});
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  if (root) root.MBUAcronymClarity=api;
})(typeof window === 'undefined' ? null : window);
