// UI workflow regression: functionality survives presentational refactor.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const inbox=fs.readFileSync(path.join(root,"inbox_assistant/ui.html"),"utf8");
const redact=fs.readFileSync(path.join(root,"redaction_app/ui.html"),"utf8");
const css=fs.readFileSync(path.join(root,"inbox_assistant/assets/ui.css"),"utf8");
const script=html=>{
  const match=html.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(match,"Inline Javascript missing");
  new vm.Script(match[1]);
  return match[1];
};
const inboxScript=script(inbox);
script(redact);
assert.match(inbox, /id="cloud-consent"[^>]*hidden/);
assert.match(inbox, /<details id="references-disclosure"/);
assert.match(inboxScript, /"decision-actions"/);
assert.match(inboxScript, /"status-error"/);
assert.match(inboxScript, /"Verschiebungsprotokoll anzeigen"/);
assert.match(inboxScript, /"Freigegeben"/);
assert.match(inboxScript, /"Prüfung offen"/);
assert.match(redact, /class="view-switch" href="\/"/);
assert.match(redact, /class="file-action" for="file"/);
assert.match(redact, /class="visually-hidden" id="file"/);
assert.match(redact, /class="review-export"/);
assert.match(redact, /class="review-confirm"/);
assert.match(redact, /<details class="quiet-details"/);
assert.match(css, /\[hidden\]\s*\{\s*display: none !important/);
assert.match(css, /height: clamp\(220px, 31vh, 340px\)/);
assert.match(css, /\.redaction-app \.review-export\s*\{\s*display: grid/);
assert.match(css, /\.provider-fieldset \.tech-option:has\(input:checked\)/);
assert.match(css, /\.redaction-app #cleaned/);
// Exercise cloud consent toggling with real code: no cloud consent in local mode.
const start=inboxScript.indexOf("function updateProviderPanel()");
const end=inboxScript.indexOf('\n$("refresh").addEventListener',start);
assert.ok(start>=0 && end>start,"Provider handler not found");
const radios=[{checked:true,handlers:{},addEventListener(event,handler){this.handlers[event]=handler;}},{checked:false,handlers:{},addEventListener(event,handler){this.handlers[event]=handler;}}];
const cloudPanel={hidden:true},checkbox={checked:false};
const doc={
 getElementById:id=>id==="cloud-consent"?cloudPanel:id==="cloud"?checkbox:null,
 querySelector:()=>({value:radios[1].checked?"jev":"local"}),
 querySelectorAll:()=>radios,
};
new vm.Script('const $ = id => document.getElementById(id);\n'+inboxScript.slice(start,end)).runInNewContext({document:doc});
assert.equal(cloudPanel.hidden,true);
radios[0].checked=false;radios[1].checked=true;radios[1].handlers.change();
assert.equal(cloudPanel.hidden,false,"Cloud permission must appear only for cloud provider");
checkbox.checked=true;
radios[1].checked=false;radios[0].checked=true;radios[0].handlers.change();
assert.equal(cloudPanel.hidden,true);
assert.equal(checkbox.checked,false,"Cloud consent must be cleared when switching back to local");
console.log("Compact UI: provider consent, layout, disclosures and controls OK");
