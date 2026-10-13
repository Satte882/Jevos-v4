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

// Echte Eventhandler mit verzögerten Antworten ausführen: keine Freigabe alter
// Ergebnisse und kein Überschreiben neuer Eingaben durch asynchrone Importe.
async function regressionTests(){
  const elements=new Map();
  const element=id=>{
    if(!elements.has(id))elements.set(id,{
      value:"",checked:false,disabled:["copy","download"].includes(id),files:[],
      textContent:"",className:"",handlers:{},hidden:id==="tech-info",attributes:{},
      setAttribute(key,value){this.attributes[key]=value;},
      addEventListener(event,handler){this.handlers[event]=handler;}
    });
    return elements.get(id);
  };
  let respond;
  const context=vm.createContext({
    document:{getElementById:element},
    fetch:()=>new Promise(resolve=>{respond=resolve;}),
    navigator:{clipboard:{writeText:async()=>{}}},console
  });
  new vm.Script(match[1]).runInContext(context);
  const run=(id,event)=>element(id).handlers[event]();
  // Info-Button muss die Technikerklärung zuverlässig öffnen und wieder schließen.
  assert.equal(element("tech-info").hidden,true);
  run("tech-info-button","click");
  assert.equal(element("tech-info").hidden,false);
  assert.equal(element("tech-info-button").attributes["aria-expanded"],"true");
  run("tech-info-button","click");
  assert.equal(element("tech-info").hidden,true);
  assert.equal(element("tech-info-button").attributes["aria-expanded"],"false");

  element("original").value="Alter Text";
  const request=run("sanitize","click");
  assert.equal(element("reviewed").disabled,true);
  element("original").value="Neuer Text";run("original","input");
  respond({ok:true,json:async()=>({text:"Veraltete Fassung",replacements:0,categories:{}})});
  await request;
  assert.equal(element("cleaned").value,"");
  assert.equal(element("copy").disabled,true);

  const current=run("sanitize","click");
  respond({ok:true,json:async()=>({text:"[PERSON_1]",replacements:1,categories:{PERSON:1}})});
  await current;
  assert.equal(element("download").disabled,true);
  element("reviewed").checked=true;run("reviewed","change");
  assert.equal(element("copy").disabled,false);
  element("cleaned").value+=" Korrektur";run("cleaned","input");
  assert.equal(element("reviewed").checked,false);
  assert.equal(element("download").disabled,true);

  let completeFile;
  element("file").files=[{name:"synthetic.txt",size:10,text:()=>new Promise(resolve=>{completeFile=resolve;})}];
  const imported=run("file","change");
  assert.equal(element("file-name").textContent,"synthetic.txt");
  run("clear","click");
  assert.equal(element("file-name").textContent,"TXT, MD oder DOCX · keine Datei ausgewählt");
  completeFile("Veralteter Dateiinhalt");await imported;
  assert.equal(element("original").value,"");
  assert.equal(element("reviewed").disabled,false);
  console.log("Redaction UI: 3 behavioral regression scenarios OK");
}
regressionTests().catch(error=>{console.error(error);process.exitCode=1;});
