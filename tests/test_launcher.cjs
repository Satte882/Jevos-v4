// Prüft Obsidian-Launcher-Registrierung ohne Desktop-Prozesse oder Vault-Zugriffe.
const assert = require("node:assert/strict");
const Module = require("node:module");
const { EventEmitter } = require("node:events");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const previous = Module._load;
const notices = [];
const spawned = [];
class Plugin { constructor(app) { this.app = app; } }
Module._load = function(id, parent, main) {
  if (id === "child_process") return { spawn: (...args) => {
    const child = new EventEmitter();
    child.stderr = new EventEmitter();
    spawned.push({args, child});
    return child;
  }};
  if (id === "obsidian") return {
    Plugin, Modal: class {}, Setting: class {},
    Notice: class { constructor(message) { notices.push(message); } }, PluginSettingTab: class {},
  };
  return previous.call(this, id, parent, main);
};
const Bridge = require("../obsidian-plugin/main.js");
Module._load = previous;
(async () => {
  const plugin = new Bridge({workspace: {on: () => ({}), getActiveViewOfType: () => null}});
  const ribbons = [];
  const commands = [];
  plugin.loadData = async () => ({repo: "C:\\mock\\Jevos-v4"});
  plugin.addSettingTab = () => {};
  plugin.registerEvent = () => {};
  plugin.addRibbonIcon = (icon, label, callback) => {
    ribbons.push({icon, label, callback});
    return {};
  };
  plugin.addCommand = cmd => commands.push(cmd);
  const routed = [];
  plugin.launchAssistant = view => routed.push(view);
  await plugin.onload();
  assert.equal(ribbons.length, 2, "Zwei Symbole in Obsidian erwartet");
  assert.deepEqual(ribbons.map(x => x.icon), ["bot", "shield-check"]);
  assert.ok(commands.some(x => x.id === "apply-approved-inbox-moves"),
    "Bestehender sicherer Obsidian-Befehl muss erhalten bleiben");
  assert.ok(commands.some(x => x.id === "open-jevos-inbox"));
  assert.ok(commands.some(x => x.id === "open-jevos-anonymize"));
  assert.ok(commands.some(x => x.id === "classify-active-note"));
  assert.ok(commands.some(x => x.id === "prepare-active-text"));
  ribbons[0].callback();
  ribbons[1].callback();
  assert.equal(routed.length,0,"Ohne aktive Markdown-Notiz keinen Auftrag erzeugen");
  assert.equal(notices.length,2);
  notices.length=0;
  const openers=[commands.find(x=>x.id==="open-jevos-inbox"),commands.find(x=>x.id==="open-jevos-anonymize")];
  openers[0].callback();openers[1].callback();
  assert.deepEqual(routed, ["inbox", "anonymize"]);
  // Exercise the real launcher method with Windows platform and synthetic processes.
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "jev-launcher-"));
  const platform = Object.getOwnPropertyDescriptor(process, "platform");
  try {
    fs.mkdirSync(path.join(temp, "scripts"));
    fs.writeFileSync(path.join(temp, "scripts", "launch-ui.ps1"), "# synthetic");
    Object.defineProperty(process, "platform", { value: "win32" });
    plugin.settings.repo = temp;
    delete plugin.launchAssistant;
    for (const [index, view] of ["inbox", "anonymize"].entries()) {
      openers[index].callback();
      const {args, child} = spawned.at(-1);
      assert.equal(args[0], "powershell.exe");
      assert.deepEqual(args[1].slice(-2), ["-View", view]);
      assert.ok(args[1].includes("-NonInteractive"));
      assert.equal(args[2].cwd, temp);
      assert.equal(args[2].windowsHide, true);
      assert.deepEqual(args[2].stdio, ["ignore", "ignore", "pipe"]);
      child.emit("close", 0);
    }
    assert.equal(notices.length, 0, "Successful launches need no error notice");
    openers[0].callback();
    spawned.at(-1).child.stderr.emit("data", Buffer.from("ParserError: missing quote"));
    spawned.at(-1).child.emit("close", 1);
    await new Promise(resolve=>setImmediate(resolve));
    assert.match(notices.at(-1), /Exitcode 1.*ParserError/);
    openers[1].callback();
    spawned.at(-1).child.emit("close", 1);
    await new Promise(resolve=>setImmediate(resolve));
    assert.match(notices.at(-1), /Python-Installation/);
    openers[0].callback();
    spawned.at(-1).child.emit("error", new Error("spawn ENOENT"));
    await new Promise(resolve=>setImmediate(resolve));
    const count = notices.length;
    spawned.at(-1).child.emit("close", -2);
    assert.equal(notices.length, count, "Spawn failure must be reported only once");
    assert.match(notices.at(-1), /ENOENT/);
    plugin.settings.repo = path.join(temp, "missing");
    openers[1].callback();
    assert.match(notices.at(-1), /Launcher fehlt/);
  } finally {
    Object.defineProperty(process, "platform", platform);
    fs.rmSync(temp, {recursive: true, force: true});
  }
  console.log("Obsidian UI launcher: 2 ribbon buttons and existing move command OK");
})().catch(error => { console.error(error); process.exitCode = 1; });
