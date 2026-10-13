// Prüft, dass das Inline-JavaScript der lokalen Bereinigungsansicht syntaktisch gültig ist.
// Es erfolgt keine Browser-Ausführung und kein Netzwerkzugriff.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const filename=path.resolve(__dirname,"..","redaction_app","ui.html");
const html=fs.readFileSync(filename,"utf8");
const match=html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(match,"Inline-Script fehlt");
new vm.Script(match[1],{filename});
for(const expected of ["api/redact","api/docx-text","reviewed","clipboard.writeText","original.addEventListener","cleaned.addEventListener"]){
  assert.ok(html.includes(expected), "Benötigte UI-Funktion fehlt: "+expected);
}
console.log("Redaction UI: Inline-JS syntaktisch korrekt und Freigabekontrollen vorhanden");
