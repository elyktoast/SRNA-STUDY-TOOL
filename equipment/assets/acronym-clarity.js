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
    ETT: 'endotracheal tube',
    FGF: 'fresh gas flow',
    FRC: 'functional residual capacity',
    HME: 'heat and moisture exchanger',
    LAST: 'local anesthetic systemic toxicity',
    MH: 'malignant hyperthermia',
    NMB: 'neuromuscular blockade',
    NMT: 'neuromuscular transmission',
    PISS: 'pin index safety system',
    PONV: 'postoperative nausea and vomiting',
    PVR: 'pulmonary vascular resistance',
    RQ: 'respiratory quotient',
    SGA: 'supraglottic airway',
    SIRS: 'systemic inflammatory response syndrome',
    SVR: 'systemic vascular resistance',
    TIVA: 'total intravenous anesthesia',
    TOF: 'train-of-four',
    VAP: 'ventilator-associated pneumonia',
    VAE: 'ventilator-associated event',
    VILI: 'ventilator-induced lung injury',
    VQ: 'ventilation–perfusion ratio',
  });
  const pattern = new RegExp('\\b(' + Object.keys(expansions).sort((a,b) => b.length-a.length).join('|') + ')\\b','g');
  function clarify(text) {
    if (typeof text !== 'string' || !text) return text;
    const introduced = new Set();
    return text.replace(pattern, (short, offset, whole) => {
      const meaning = expansions[short];
      if (introduced.has(short)) return short;
      introduced.add(short);
      // Avoid duplicating an expansion already directly present in the source text.
      const pre = whole.slice(Math.max(0,offset-meaning.length-6),offset).toLowerCase();
      const post = whole.slice(offset+short.length,offset+short.length+meaning.length+6).toLowerCase();
      if (pre.includes(meaning.toLowerCase()) || post.includes(meaning.toLowerCase())) return short;
      return meaning + ' (' + short + ')';
    });
  }
  const api=Object.freeze({clarify,expansions});
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  if (root) root.MBUAcronymClarity=api;
})(typeof window === 'undefined' ? null : window);
