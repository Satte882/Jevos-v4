/* Obsidian Community-Plugin: Nur auf ausdrücklichen Befehl freigegebene Verschiebungen ausführen.
 * Verwendet ausschließlich lokale Dateien und Obsidian FileManager.renameFile().
 */
const { Plugin, Modal, Setting, Notice, PluginSettingTab } = require("obsidian");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawn } = require("child_process");
const DEFAULT_REPO = "C:\\Users\\user\\Documents\\GitHub\\Jevos-v4";

function normalized(s) {
  return path.resolve(s).replace(/[\\/]+$/, "").toLowerCase();
}
function within(root, target) {
  const p = path.resolve(root, ...target.split("/"));
  return p.startsWith(path.resolve(root) + path.sep) && !target.split("/").some(x => !x || x === "." || x === ".." || x.includes("\\"));
}
function sha(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}
function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = file + ".partial";
  fs.writeFileSync(temporary, JSON.stringify(value, null, 2), { encoding: "utf8" });
  fs.renameSync(temporary, file);
}
class ConfirmMoves extends Modal {
  constructor(app, plan, resolve) {
    super(app);
    this.plan = plan;
    this.done = resolve;
    this.resolved = false;
  }
  onOpen() {
    this.titleEl.setText("Inbox-Verschiebungen freigeben");
    this.contentEl.createEl("p", {text: this.plan.moves.length + " Notiz(en) wurden geprüft. Sicherung ist vorhanden."});
    const ul = this.contentEl.createEl("ul");
    for (const move of this.plan.moves) {
      ul.createEl("li", {text: move.source + "  →  " + move.target});
    }
    this.contentEl.createEl("p", {text: "Obsidian aktualisiert Links gemäß deiner Vault-Einstellungen."});
    new Setting(this.contentEl)
      .addButton(button => button.setButtonText("Abbrechen").onClick(() => this.close()))
      .addButton(button => button.setCta().setButtonText("Jetzt verschieben").onClick(() => {
        this.resolved = true;
        this.done(true);
        this.close();
      }));
  }
  onClose() {
    this.contentEl.empty();
    if (!this.resolved) this.done(false);
  }
}
class BridgeSettings extends PluginSettingTab {
  constructor(app, plugin) { super(app, plugin); this.plugin = plugin; }
  display() {
    const el = this.containerEl;
    el.empty();
    new Setting(el).setName("Repository-Verzeichnis")
      .setDesc("Der Ordner enthält .local/bridge/pending.json. Muss außerhalb des Vaults liegen.")
      .addText(input => input.setPlaceholder(DEFAULT_REPO).setValue(this.plugin.settings.repo)
        .onChange(async value => {
          this.plugin.settings.repo = value;
          await this.plugin.saveData(this.plugin.settings);
        }));
  }
}
module.exports = class JevInboxBridge extends Plugin {
  async onload() {
    this.settings = Object.assign({repo: DEFAULT_REPO}, await this.loadData() || {});
    this.addSettingTab(new BridgeSettings(this.app, this));
    // Ein Klick startet die lokale Oberfläche bei Bedarf und öffnet den Standardbrowser.
    // Vorhandene Prüf- und Verschiebungsbefehle bleiben unverändert.
    const launch = view => {
      try { this.launchAssistant(view); }
      catch (error) { new Notice("Jevos: " + error.message, 10000); }
    };
    this.addRibbonIcon("bot", "Jevos – Inbox-Assistent öffnen", () => launch("inbox"));
    this.addRibbonIcon("shield-check", "Jevos – Textbereinigung öffnen", () => launch("anonymize"));
    this.addCommand({
      id: "open-jevos-inbox",
      name: "Jevos Inbox-Assistent öffnen",
      callback: () => launch("inbox"),
    });
    this.addCommand({
      id: "open-jevos-anonymize",
      name: "Jevos Textbereinigung öffnen",
      callback: () => launch("anonymize"),
    });
    this.addCommand({
      id: "apply-approved-inbox-moves",
      name: "Freigegebene Inbox-Verschiebungen anwenden",
      callback: async () => {
        try { await this.apply(); }
        catch (error) { console.error("[Jev Inbox Bridge]", error); new Notice("Inbox Bridge: " + error.message, 10000); }
      }
    });
  }
  launchAssistant(view) {
    if (process.platform !== "win32")
      throw new Error("Der Ein-Klick-Launcher unterstützt derzeit Windows.");
    if (!["inbox", "anonymize"].includes(view))
      throw new Error("Unbekannte Ansicht.");
    const repo = path.resolve(this.settings.repo);
    const launcher = path.join(repo, "scripts", "launch-ui.ps1");
    if (!fs.existsSync(launcher) || !fs.statSync(launcher).isFile())
      throw new Error("Launcher fehlt. GitHub-Repository aktualisieren und Plugin-Einstellungen prüfen.");
    const child = spawn("powershell.exe",
      ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", launcher, "-View", view],
      { cwd: repo, windowsHide: true, stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    let spawnFailed = false;
    child.stderr.on("data", data => {
      // Bounded diagnostics, including parse errors before the script's catch block.
      stderr = (stderr + data.toString()).slice(-4000);
    });
    child.on("error", error => {
      spawnFailed = true;
      new Notice("Jevos konnte nicht gestartet werden: " + error.message, 10000);
    });
    child.on("close", code => {
      if (code !== 0 && !spawnFailed) {
        new Notice("Jevos konnte nicht gestartet werden (Exitcode " + code + "). " +
          (stderr.trim() || "Launcher und Python-Installation prüfen."), 15000);
      }
    });
  }
  getRoot() {
    const adapter = this.app.vault.adapter;
    const root = adapter.basePath || (adapter.getBasePath && adapter.getBasePath());
    if (!root) throw new Error("Nur ein lokaler Desktop-Vault wird unterstützt.");
    return path.resolve(root);
  }
  preflight(plan, repo, root) {
    if (!plan || plan.version !== 1 || plan.status !== "awaiting-obsidian" ||
        typeof plan.batch_id !== "string" || !Array.isArray(plan.moves) || !plan.moves.length)
      throw new Error("Ungültiger oder leerer Ausführungsplan.");
    if (normalized(plan.vault) !== normalized(root))
      throw new Error("Plan gehört zu einem anderen Vault.");
    if (typeof plan.inbox !== "string" || !within(root, plan.inbox))
      throw new Error("Inbox-Pfad im Plan ungültig.");
    if (!plan.backup || typeof plan.backup.path !== "string" ||
        !/^[a-f0-9]{64}$/.test(plan.backup.sha256))
      throw new Error("Sicherungsnachweis fehlt.");
    const backupPath = path.resolve(plan.backup.path);
    const backupRoot = path.resolve(repo, ".local", "backups");
    if (!(backupPath.startsWith(backupRoot + path.sep)) ||
        !fs.existsSync(backupPath) || sha(backupPath) !== plan.backup.sha256)
      throw new Error("Sicherung nicht vorhanden oder SHA-256 ungültig.");
    for (const move of plan.moves) {
      if (!move || typeof move.source !== "string" || typeof move.target !== "string" ||
          !within(root, move.source) || !within(root, move.target) ||
          !move.source.startsWith(plan.inbox + "/") ||
          move.source.slice(plan.inbox.length + 1).includes("/") ||
          !move.source.toLowerCase().endsWith(".md") ||
          move.target.startsWith(plan.inbox + "/") ||
          !/^[a-f0-9]{64}$/.test(move.sha256))
        throw new Error("Ungültige Quell- oder Zielpfade im Plan.");
      const src = path.join(root, ...move.source.split("/"));
      const dst = path.join(root, ...move.target.split("/"));
      if (!fs.existsSync(src) || fs.lstatSync(src).isSymbolicLink() || sha(src) !== move.sha256)
        throw new Error("Notiz fehlt oder wurde verändert: " + move.source);
      if (fs.existsSync(dst)) throw new Error("Zieldatei existiert: " + move.target);
      const parent = path.dirname(dst);
      if (!fs.existsSync(parent) || !fs.statSync(parent).isDirectory())
        throw new Error("Zielordner existiert nicht: " + move.target);
      const obFile = this.app.vault.getAbstractFileByPath(move.source);
      if (!obFile || obFile.extension !== "md")
        throw new Error("Obsidian kennt die Quelldatei nicht: " + move.source);
    }
  }
  async apply() {
    const repo = path.resolve(this.settings.repo);
    const root = this.getRoot();
    if (normalized(repo) === normalized(root) || normalized(repo).startsWith(normalized(root) + path.sep))
      throw new Error("Repository muss außerhalb des Vaults liegen.");
    const base = path.join(repo, ".local", "bridge");
    const pendingFile = path.join(base, "pending.json");
    const resultFile = path.join(base, "result.json");
    if (!fs.existsSync(pendingFile)) throw new Error("Kein freigegebener Stapel vorhanden.");
    const plan = JSON.parse(fs.readFileSync(pendingFile, "utf8"));
    if (fs.existsSync(resultFile)) {
      const old = JSON.parse(fs.readFileSync(resultFile, "utf8"));
      if (old.batch_id === plan.batch_id) throw new Error("Dieser Stapel wurde bereits ausgeführt.");
    }
    this.preflight(plan, repo, root);
    const accepted = await new Promise(resolve => new ConfirmMoves(this.app, plan, resolve).open());
    if (!accepted) return;
    const result = {batch_id: plan.batch_id, finished_at: null, results: []};
    for (const move of plan.moves) {
      try {
        // Revalidate immediately: other move operations may update link-bearing notes.
        this.preflightOne(move, plan, root);
        const file = this.app.vault.getAbstractFileByPath(move.source);
        if (!file || file.extension !== "md") throw new Error("Quelldatei nicht mehr bekannt.");
        await this.app.fileManager.renameFile(file, move.target);
        result.results.push({source: move.source, target: move.target, status: "moved"});
      } catch (error) {
        result.results.push({source: move.source, target: move.target,
                             status: "failed", error: String(error.message || error)});
        break; // Keine weiteren Verschiebungen nach einem Fehler.
      } finally {
        result.finished_at = new Date().toISOString();
        atomicJson(resultFile, result);
      }
    }
    const ok = result.results.filter(x => x.status === "moved").length;
    new Notice("Inbox Bridge: " + ok + " Datei(en) verschoben; Ergebnis im lokalen Assistenten.", 9000);
  }
  preflightOne(move, plan, root) {
    if (!within(root, move.source) || !within(root, move.target) ||
        !move.source.startsWith(plan.inbox + "/"))
      throw new Error("Pfad nicht mehr gültig.");
    const src = path.join(root, ...move.source.split("/"));
    const dst = path.join(root, ...move.target.split("/"));
    if (!fs.existsSync(src) || sha(src) !== move.sha256)
      throw new Error("Quelldatei seit Freigabe geändert.");
    if (fs.existsSync(dst)) throw new Error("Ziel bereits vorhanden.");
  }
};
