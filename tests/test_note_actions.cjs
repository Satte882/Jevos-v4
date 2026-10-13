// Exercise real plugin actions against a synthetic Obsidian surface and files.
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),os=require("node:os"),crypto=require("node:crypto"),Module=require("node:module");
const notices=[],modals=[];
class Element {
  constructor(){this.children=[];this.textContent="";this.hidden=false;this.style={};}
  createEl(tag,options={}){const el=new Element();el.textContent=options.text||"";this.children.push(el);return el;}
  createDiv(){return this.createEl("div");} empty(){this.children=[];} setText(text){this.textContent=text;}
}
class Control {
  constructor(){this.disabled=false;this.value="";this.options={};}
  setButtonText(text){this.text=text;return this;} setCta(){return this;}
  setDisabled(value){this.disabled=value;return this;} setValue(value){this.value=value;return this;}
  addOptions(values){Object.assign(this.options,values);return this;} addOption(key,value){this.options[key]=value;return this;}
  onClick(fn){this.click=fn;return this;} onChange(fn){this.change=fn;return this;}
}
class Setting {
  constructor(parent){this.settingEl=parent.createDiv();}
  setName(){return this;} setDesc(){return this;}
  addButton(fn){fn(new Control());return this;} addDropdown(fn){fn(new Control());return this;} addToggle(fn){fn(new Control());return this;}
}
class Modal {
  constructor(app){this.app=app;this.titleEl=new Element();this.contentEl=new Element();}
  open(){modals.push(this);this.onOpen();} close(){this.onClose();}
}
class Plugin {constructor(app){this.app=app;}}
const load=Module._load;
Module._load=function(id,parent,main){if(id==="obsidian")return {Plugin,Modal,Setting,MarkdownView:class{},PluginSettingTab:class{},Notice:class{constructor(text){notices.push(text);}}};return load.call(this,id,parent,main);};
const Bridge=require("../obsidian-plugin/main.js");Module._load=load;
const temporary=fs.mkdtempSync(path.join(os.tmpdir(),"jev-note-actions-"));
async function main(){
  const root=path.join(temporary,"vault"),inbox="Inbox",file={path:"Inbox/Synthetic.md",basename:"Synthetic",extension:"md"};
  fs.mkdirSync(path.join(root,inbox),{recursive:true});
  const state={text:"Unsaved Alice note",selection:"Alice",mode:"source",saved:0};
  const editor={getValue:()=>state.text,getSelection:()=>state.selection};
  const view={file,editor,getMode:()=>state.mode,getViewData:()=>state.text,save:async()=>{state.saved++;fs.writeFileSync(path.join(root,file.path),state.text);}};
  const app={workspace:{getActiveViewOfType:()=>view},vault:{adapter:{basePath:root},getAbstractFileByPath:source=>source===file.path?file:null}};
  const plugin=new Bridge(app);
  plugin.settings={repo:temporary};
  fs.writeFileSync(path.join(temporary,"config.json"),JSON.stringify({vault:root,inbox:path.join(root,inbox)}));
  let sent,launched=[];
  plugin.connection=async()=>({token:"test",vault:root,inbox});
  plugin.launchAssistant=async(view,options)=>{launched.push({view,options});};
  plugin.api=async(connection,route,data)=>{sent={route,data};return {handoff_id:"a".repeat(64)};};
  const snapshot=plugin.captureNote();
  state.text="Changed after invocation";state.selection="Changed selection";
  await plugin.prepareText(snapshot);
  assert.equal(sent.data.text,"Alice");assert.equal(sent.data.kind,"selection");assert.equal(state.saved,0);
  assert.deepEqual(launched.at(-1),{view:"anonymize",options:{handoffId:"a".repeat(64)}});
  state.selection=" ";await plugin.prepareText(plugin.captureNote());assert.equal(sent.data.kind,"note");assert.equal(sent.data.text,state.text);
  state.mode="preview";state.selection="stale selection";
  await plugin.prepareText(plugin.captureNote());assert.equal(sent.data.kind,"note");assert.equal(state.saved,0);
  await assert.rejects(plugin.prepareText({...snapshot,selection:"",text:" "}),/leer/);
  await assert.rejects(plugin.prepareText({...snapshot,selection:"x".repeat(100001)}),/100.000/);
  state.mode="source";state.text="Latest unsaved note";
  await plugin.classifyNote(plugin.captureNote());assert.equal(state.saved,1);assert.equal(fs.readFileSync(path.join(root,file.path),"utf8"),state.text);
  const modal=plugin.reviewModal;
  assert.equal(modal.cloudSetting.settingEl.style.display,"none");
  modal.providerControl.change("jev");assert.equal(modal.cloudSetting.settingEl.style.display,"");
  modal.providerControl.change("local");assert.equal(modal.cloudSetting.settingEl.style.display,"none");
  await assert.rejects(plugin.classifyNote(plugin.captureNote()),/bereits geöffnet/);
  const hash=crypto.createHash("sha256").update(state.text).digest("hex");
  const analysis={manual_review:true,primary:null,alternatives:[{folder:"Knowledge",probability:.4},{folder:"Other",probability:.35}],evidence:[{folder:"Knowledge",references:[{title:"Example",snippet:"Original evidence"}]}]};
  const requests=[];
  plugin.api=async(c,route,data)=>{requests.push({route,data});if(route==="/api/analyze")return {job_id:"job-1"};return {job:{id:"job-1",status:"finished",completed:1,total:1},folders:["Knowledge","Other"],rows:[{source:file.path,sha256:hash,analysis}]};};
  await modal.analyze();assert.equal(modal.approveButton.disabled,true);assert.equal(modal.startButton.disabled,false);
  assert.equal(requests[0].data.source,file.path);assert.equal(requests[0].data.expected_sha256,hash);assert.equal(requests[0].data.provider,"local");
  modal.destination="Knowledge";modal.updateTarget();assert.equal(modal.approveButton.disabled,false);
  modal.provider="jev";modal.consent=false;const before=requests.length;await modal.analyze();assert.equal(requests.length,before);
  modal.provider="local";
  plugin.api=async(c,route,data)=>{requests.push({route,data});if(route==="/api/prepare")return {batch_id:"single-batch"};return {};};
  plugin.apply=async id=>{assert.equal(id,"single-batch");return "cancelled";};
  await modal.prepare();assert.equal(plugin.reviewModal,null);
  assert.equal(requests.find(r=>r.route==="/api/prepare").data.source,file.path);
  assert.equal(requests.find(r=>r.route==="/api/cancel").data.batch_id,"single-batch");
  plugin.connection=async()=>({token:"test",vault:path.join(temporary,"wrong"),inbox});
  await assert.rejects(plugin.classifyNote(plugin.captureNote()),/anderen Vault/);
  plugin.connection=async()=>({token:"test",vault:root,inbox:"OtherInbox"});
  await assert.rejects(plugin.classifyNote(plugin.captureNote()),/konfigurierten Inbox/);
  view.file=null;assert.throws(()=>plugin.captureNote(),/Markdown-Notiz/);
  console.log("Obsidian note actions: snapshots, selection, save, review, consent and scoped cancellation OK");
}
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>{
  const resolved=path.resolve(temporary);
  if(path.dirname(resolved)!==path.resolve(os.tmpdir())||!path.basename(resolved).startsWith("jev-note-actions-"))throw new Error("Unsafe test cleanup");
  fs.rmSync(resolved,{recursive:true,force:true});
});
