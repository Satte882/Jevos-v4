// Smoke + real click-behavior test for technology-info buttons; no browser/network.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const inbox = fs.readFileSync(path.join(root, "inbox_assistant/ui.html"), "utf8");
const redaction = fs.readFileSync(path.join(root, "redaction_app/ui.html"), "utf8");
function inlineScript(html) {
  const found = html.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(found, "Inline-Script fehlt");
  new vm.Script(found[1]);
  return found[1];
}
const js = inlineScript(inbox);
inlineScript(redaction);
assert.match(inbox, /Hier arbeitet Jev \(System-One-KI\)/);
assert.match(inbox, /jevos-v4 · lokal/);
assert.match(inbox, /Jev · TypeSafe Cloud/);
assert.match(redaction, /Hier arbeitet spaCy · de_core_news_md/);
assert.match(redaction, /vollständig lokal · kein Jev/);
assert.match(redaction, /spaCy.*?Python-Bibliothek/s);
assert.match(redaction, /Regex.*?E-Mails/s);

const buttons = ["local-info", "cloud-info"].map(id => ({
  dataset: {infoTarget:id},
  attributes: {},
  setAttribute(name,value) {this.attributes[name]=value;},
  addEventListener(name,handler) {if(name==="click") this.click=handler;},
}));
const panels = {
  "local-info": {hidden:true},
  "cloud-info": {hidden:true},
};
const doc = {
  querySelectorAll() {return buttons;},
  getElementById(id) {return panels[id];},
};
const start = js.indexOf('document.querySelectorAll("[data-info-target]")');
const end = js.indexOf("\nconst elem = ",start);
assert.ok(start>=0 && end>start, "Informationsbutton-Handler nicht gefunden");
new vm.Script("const $ = id => document.getElementById(id);\n"+js.slice(start,end)).runInNewContext({document:doc});
buttons[0].click();
assert.equal(panels["local-info"].hidden,false);
assert.equal(buttons[0].attributes["aria-expanded"],"true");
buttons[1].click();
assert.equal(panels["local-info"].hidden,true);
assert.equal(panels["cloud-info"].hidden,false);
assert.equal(buttons[0].attributes["aria-expanded"],"false");
buttons[1].click();
assert.equal(panels["cloud-info"].hidden,true);
console.log("UI: Jev and spaCy technology labels and info-button behavior OK");
