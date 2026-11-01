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
  const regional = Object.freeze({SAB:'subarachnoid block', CSE:'combined spinal–epidural',
    PNB:'peripheral nerve block', TAP:'transversus abdominis plane',
    ESP:'erector spinae plane', QL:'quadratus lumborum',
    PENG:'pericapsular nerve group', ACB:'adductor canal block',
    FNB:'femoral nerve block', ISB:'interscalene block',
    SCB:'supraclavicular block', PDPH:'post-dural puncture headache'});
  // Normalize only unambiguous everyday anesthesia terms for display.
  // Preserve canonical question text, answers, and historical submissions.
  const familiar = Object.freeze([
    [/\bblood pressure\b/gi, 'BP'],
    [/\bend[- ]tidal (?:carbon dioxide|CO2)\b/gi, 'EtCO2'],
    [/\bheart rate\b/gi, 'HR'],
    [/\bmean arterial pressure\b/gi, 'MAP'],
    [/\boperating room\b/gi, 'OR'],
    [/\bpositive end[- ]expiratory pressure\b/gi, 'PEEP'],
    [/\bpeak inspiratory pressure\b/gi, 'PIP'],
    [/\bplateau pressure\b/gi, 'Pplat'],
    [/\bfraction of inspired oxygen\b/gi, 'FiO2'],
    [/\bperipheral oxygen saturation\b/gi, 'SpO2'],
  ]);
  function normalizeFamiliar(text) {
    for (const [pattern, short] of familiar) {
      text = text.replace(pattern, (match, offset, whole) => {
        const following = whole.slice(offset + match.length);
        // Do not duplicate an acronym already supplied by the author.
        if (new RegExp('^\\\s*\\\(' + short + '\\\)', 'i').test(following)) return match;
        return short;
      });
    }
    return text;
  }
  function clarify(text, options={}) {
    if (typeof text !== 'string' || !text) return text;
    text = normalizeFamiliar(text);
    if (/regional|neuraxial/i.test(String(options.topic||''))) {
      const re = new RegExp('\\b(?:' + Object.keys(regional).join('|') + ')\\b','g');
      return text.replace(re, (short, offset, full) => {
        const phrase=regional[short];
        const previous=full.slice(Math.max(0,offset-phrase.length-4),offset).toLowerCase();
        return previous.includes(phrase.toLowerCase()) ? short : phrase+' ('+short+')';
      });
    }
    if (/respiratory|ventilat|airway mechanics/i.test(String(options.topic||''))) {
      text = text.replace(/\btidal volume\b(?!\s*\(Vt\))/gi, 'Vt')
        .replace(/\bminute ventilation\b(?!\s*\(MV\))/gi, 'MV')
        .replace(/\bTV\b/g, 'Vt').replace(/\bVE\b/g, 'MV');
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
        const re=new RegExp('\\b'+meaning.replace(/ /g,'\\s+')+'\\b','i');
        result=result.replace(re, m => m+' ('+short+')');
      }
    }
    return result;
  }
  const api=Object.freeze({clarify,expansions});
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  if (root) root.MBUAcronymClarity=api;
})(typeof window === 'undefined' ? null : window);
