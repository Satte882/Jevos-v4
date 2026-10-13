// Synthetic filesystem checks only: never launches Obsidian or modifies a real vault.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const crypto = require("node:crypto");
const Module = require("node:module");
const previous = Module._load;
class Plugin { constructor(app) { this.app = app; } }
Module._load = function (id, parent, main) {
  if (id === "obsidian") return {Plugin, Modal: class {}, Setting: class {},
    Notice: class {}, PluginSettingTab: class {}};
  return previous.call(this, id, parent, main);
};
const Bridge = require("../obsidian-plugin/main.js");
Module._load = previous;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "jev-bridge-test-"));
try {
  const vault = path.join(temp, "vault");
  const repo = path.join(temp, "repo");
  const inbox = "ZZZZZ_Inbox_noch_Einzuordnen";
  const folder = "Wissen";
  const text = "Synthetic [[Test Link]]";
  fs.mkdirSync(path.join(vault, inbox), {recursive:true});
  fs.mkdirSync(path.join(vault, folder), {recursive:true});
  fs.mkdirSync(path.join(repo, ".local", "backups"), {recursive:true});
  const source = inbox + "/note.md";
  const target = folder + "/note.md";
  const input = path.join(vault, inbox, "note.md");
  fs.writeFileSync(input, text);
  const sha = value => crypto.createHash("sha256").update(value).digest("hex");
  const backup = path.join(repo, ".local", "backups", "backup.zip");
  fs.writeFileSync(backup, "synthetic-backup-data");
  const plan = {version:1,batch_id:"synthetic-batch",status:"awaiting-obsidian",
    vault,inbox,
    backup:{path:backup,sha256:sha(fs.readFileSync(backup))},
    moves:[{source,target,sha256:sha(fs.readFileSync(input))}]};
  const app = {vault:{adapter:{basePath:vault},
      getAbstractFileByPath: file => file===source?{path:source,extension:"md"}:null}};
  const plugin = new Bridge(app);
  plugin.preflight(plan,repo,vault);
  plugin.preflightOne(plan.moves[0],plan,vault);
  assert.equal(fs.readFileSync(input,"utf8"),text);
  assert.equal(fs.existsSync(path.join(vault,folder,"note.md")),false);
  fs.writeFileSync(path.join(vault,folder,"note.md"),"Collision");
  assert.throws(()=>plugin.preflight(plan,repo,vault),/Zieldatei existiert/);
  fs.unlinkSync(path.join(vault,folder,"note.md"));
  fs.writeFileSync(input,"changed");
  assert.throws(()=>plugin.preflightOne(plan.moves[0],plan,vault),/geändert/);
  fs.writeFileSync(input,text);
  assert.throws(()=>plugin.preflight({...plan,vault:repo},repo,vault),/anderen Vault/);
  assert.throws(()=>plugin.preflight({...plan,backup:{...plan.backup,sha256:"0".repeat(64)}},repo,vault),/Sicherung/);
  console.log("Obsidian bridge preflight: synthetic filesystem tests OK");
} finally {
  fs.rmSync(temp,{recursive:true,force:true});
}
