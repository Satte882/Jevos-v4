// Prüft Obsidian-Launcher-Registrierung ohne Desktop-Prozesse oder Vault-Zugriffe.
const assert = require("node:assert/strict");
const Module = require("node:module");
const previous = Module._load;
class Plugin { constructor(app) { this.app = app; } }
Module._load = function(id, parent, main) {
  if (id === "obsidian") return {
    Plugin, Modal: class {}, Setting: class {}, Notice: class {}, PluginSettingTab: class {},
  };
  return previous.call(this, id, parent, main);
};
const Bridge = require("../obsidian-plugin/main.js");
Module._load = previous;
(async () => {
  const plugin = new Bridge({});
  const ribbons = [];
  const commands = [];
  plugin.loadData = async () => ({repo: "C:\\mock\\Jevos-v4"});
  plugin.addSettingTab = () => {};
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
  ribbons[0].callback();
  ribbons[1].callback();
  assert.deepEqual(routed, ["inbox", "anonymize"]);
  console.log("Obsidian UI launcher: 2 ribbon buttons and existing move command OK");
})().catch(error => { console.error(error); process.exitCode = 1; });
