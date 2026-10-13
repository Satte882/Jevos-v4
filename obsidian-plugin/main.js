/* Obsidian Community-Plugin: Nur auf ausdrücklichen Befehl freigegebene Verschiebungen ausführen.
 * Verwendet ausschließlich lokale Dateien und Obsidian FileManager.renameFile().
 */
const { Plugin, Modal, Setting, Notice, PluginSettingTab, MarkdownView, requestUrl } = require("obsidian");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawn } = require("child_process");
const DEFAULT_REPO = "C:\\Users\\user\\Documents\\GitHub\\Jevos-v4";
const LOCAL_URL = "http://127.0.0.1:8765";

class ReviewNote extends Modal {
  constructor(plugin, snapshot, connection) {
    super(plugin.app);
    this.plugin = plugin; this.snapshot = snapshot; this.connection = connection;
    this.active = true; this.running = false; this.provider = "local"; this.consent = false;
    this.includeArchives = false; this.destination = ""; this.analysis = null;
  }
  onOpen() {
    this.titleEl.setText("Einordnen: " + this.snapshot.title);
    this.contentEl.createEl("p", {text: "Prüfe den Zielordner und die Originalpassagen. Verschoben wird erst nach einer zweiten Freigabe."});
    new Setting(this.contentEl).setName("Entscheidungsmodell").addDropdown(dropdown => {
      this.providerControl = dropdown;
      dropdown.addOptions({local: "jevos-v4 lokal", jev: "Jev · TypeSafe Cloud"}).setValue("local").onChange(value => {
        this.provider = value; this.consent = false;
        this.cloudToggle.setValue(false); this.cloudSetting.settingEl.style.display = value === "jev" ? "" : "none";
      });
    });
    this.cloudSetting = new Setting(this.contentEl).setName("Cloud-Übertragung freigeben")
      .setDesc("Diese Notiz und ausgewählte Referenzpassagen werden an TypeSafe übertragen; mögliche API-Kosten.")
      .addToggle(toggle => {this.cloudToggle = toggle; toggle.setValue(false).onChange(value => {this.consent = value;});});
    this.cloudSetting.settingEl.style.display = "none";
    new Setting(this.contentEl).setName("Archiv- und Backlog-Ziele einbeziehen").addToggle(toggle => {
      this.archiveControl = toggle; toggle.setValue(false).onChange(value => {this.includeArchives = value;});
    });
    new Setting(this.contentEl).addButton(button => {
      this.startButton = button; button.setButtonText("Vorschlag berechnen").setCta().onClick(() => this.analyze());
    });
    this.statusEl = this.contentEl.createEl("p", {text: "Bereit für die lokale Analyse."});
    this.resultsEl = this.contentEl.createDiv();
  }
  async analyze() {
    if (this.running || !this.active) return;
    if (this.provider === "jev" && !this.consent) {
      this.statusEl.setText("Cloud erfordert deine ausdrückliche Freigabe für diesen Auftrag."); return;
    }
    this.running = true; this.analysis = null; this.resultsEl.empty();
    for (const control of [this.startButton, this.providerControl, this.cloudToggle, this.archiveControl]) control.setDisabled(true);
    try {
      const started = await this.plugin.api(this.connection, "/api/analyze", {
        provider: this.provider, cloud_consent: this.provider === "jev" && this.consent,
        source: this.snapshot.source, expected_sha256: this.snapshot.sha256,
        limit: 1, include_archives: this.includeArchives,
      });
      while (this.active) {
        const state = await this.plugin.api(this.connection, "/api/state");
        if (state.job.id !== started.job_id) throw new Error("Der Analyselauf wurde ersetzt. Bitte erneut starten.");
        this.statusEl.setText("Analyse: " + (state.job.completed || 0) + " / " + (state.job.total || 1));
        if (state.job.status !== "running") {
          if (state.job.status === "failed") throw new Error(state.job.error);
          const row = state.rows.find(item => item.source === this.snapshot.source);
          if (!row || row.sha256 !== this.snapshot.sha256) throw new Error("Notiz seit dem Aufruf geändert. Bitte erneut aus Obsidian starten.");
          if (row.error) throw new Error(row.error.error);
          if (!row.analysis) throw new Error("Kein aktuelles Analyseergebnis vorhanden.");
          this.analysis = row.analysis; this.showResult(state.folders); break;
        }
        await new Promise(resolve => setTimeout(resolve, 1500));
      }
    } catch (error) { if (this.active) this.statusEl.setText(error.message); }
    finally {
      this.running = false;
      if (this.active) for (const control of [this.startButton, this.providerControl, this.cloudToggle, this.archiveControl]) control.setDisabled(false);
      if (this.active && this.analysis) this.updateTarget();
    }
  }
  showResult(folders) {
    this.resultsEl.empty();
    const a = this.analysis;
    this.statusEl.setText(a.manual_review ? "Kein eindeutiges Ziel – bitte selbst auswählen." : "Vorgeschlagen: " + a.primary);
    this.resultsEl.createEl("p", {text: "Modellwerte sind keine gemessene Trefferquote."});
    this.destination = a.primary || "";
    for (const alternative of a.alternatives.slice(0, 3)) {
      new Setting(this.resultsEl).setName(alternative.folder)
        .setDesc(Math.round(alternative.probability * 100) + " % Modellwert")
        .addButton(button => button.setButtonText("Vergleichen").onClick(() => {
          this.destination = alternative.folder; this.targetControl.setValue(this.destination); this.updateTarget();
        }));
    }
    new Setting(this.resultsEl).setName("Zielordner").addDropdown(dropdown => {
      this.targetControl = dropdown; dropdown.addOption("", "Zielordner wählen…");
      for (const folder of folders) dropdown.addOption(folder, folder);
      dropdown.setValue(this.destination).onChange(value => {this.destination = value; this.updateTarget();});
    });
    this.evidenceEl = this.resultsEl.createDiv();
    const actions = new Setting(this.resultsEl);
    actions.settingEl.style.position = "sticky";
    actions.settingEl.style.bottom = "0";
    actions.settingEl.style.background = "var(--background-primary)";
    actions.settingEl.style.zIndex = "1";
    actions.addButton(button => {
      this.approveButton = button;
      button.setButtonText("Bestätigen und sichern").setCta().onClick(() => this.prepare());
    }).addButton(button => {
      this.deferButton = button;
      button.setButtonText("Zurückstellen").onClick(async () => {
        if (this.running) return;
        try {await this.plugin.api(this.connection, "/api/decide", {source: this.snapshot.source,
          expected_sha256: this.snapshot.sha256, status: "deferred"}); this.close();}
        catch (error) {this.statusEl.setText(error.message);}
      });
    });
    this.updateTarget();
  }
  updateTarget() {
    this.approveButton.setDisabled(!this.destination || this.running);
    this.evidenceEl.empty();
    const folder = this.destination || this.analysis.alternatives[0]?.folder;
    this.evidenceEl.createEl("h4", {text: "Referenzen für " + (folder || "das gewählte Ziel")});
    const references = this.analysis.evidence?.find(item => item.folder === folder)?.references || [];
    if (!references.length) this.evidenceEl.createEl("p", {text: "Für diesen Ordner wurden keine Referenzpassagen übergeben."});
    for (const reference of references) {
      this.evidenceEl.createEl("strong", {text: reference.title});
      this.evidenceEl.createEl("blockquote", {text: reference.snippet});
    }
  }
  async prepare() {
    if (this.running || !this.destination || !this.analysis) return;
    this.running = true;
    for (const control of [this.approveButton, this.deferButton, this.startButton, this.targetControl]) control.setDisabled(true);
    let plan;
    try {
      const file = this.plugin.app.vault.getAbstractFileByPath(this.snapshot.source);
      if (!file || sha(path.join(this.snapshot.root, this.snapshot.source)) !== this.snapshot.sha256)
        throw new Error("Notiz seit der Analyse geändert. Bitte erneut aus Obsidian starten.");
      this.statusEl.setText("Notizen und Canvas-Dateien werden für mögliche Linkänderungen gesichert…");
      await this.plugin.api(this.connection, "/api/decide", {source: this.snapshot.source,
        expected_sha256: this.snapshot.sha256, status: "approved", destination: this.destination});
      plan = await this.plugin.api(this.connection, "/api/prepare", {confirm: "PREPARE",
        source: this.snapshot.source, expected_sha256: this.snapshot.sha256});
      this.statusEl.setText("Sicherung erstellt. Verschiebung bitte im zweiten Dialog freigeben.");
      const outcome = await this.plugin.apply(plan.batch_id);
      if (outcome === "cancelled") {
        await this.plugin.api(this.connection, "/api/cancel", {confirm: "CANCEL", batch_id: plan.batch_id});
        new Notice("Verschiebung abgebrochen. Das Backup bleibt erhalten.");
      }
      this.close();
    } catch (error) {
      if (plan) {
        try {
          await this.plugin.api(this.connection, "/api/cancel", {confirm: "CANCEL", batch_id: plan.batch_id});
          this.statusEl.setText(error.message + " Plan verworfen; Sicherung bleibt erhalten.");
        } catch (_) {this.statusEl.setText(error.message + " Der gesicherte Plan bleibt zur Prüfung erhalten.");}
      } else this.statusEl.setText(error.message);
    } finally {
      this.running = false;
      if (this.active) {this.startButton.setDisabled(false); this.deferButton.setDisabled(false);
        this.targetControl.setDisabled(false); this.updateTarget();}
    }
  }
  onClose() {this.active = false; if (this.plugin.reviewModal === this) this.plugin.reviewModal = null;}
}

function normalized(s) {
  return path.resolve(s).replace(/[\\/]+$/, "").toLowerCase();
}
function within(root, target) {
  const p = path.resolve(root, ...target.split("/"));
  return p.startsWith(path.resolve(root) + path.sep) && !target.split("/").some(x => !x || x === "." || x === ".." || x.includes("\\"));
}
function sha(file) {
  const digest = crypto.createHash("sha256");
  const fd = fs.openSync(file, "r");
  try {
    const block = Buffer.allocUnsafe(1024 * 1024);
    let count;
    while ((count = fs.readSync(fd, block, 0, block.length, null)) > 0) digest.update(block.subarray(0, count));
    return digest.digest("hex");
  } finally {fs.closeSync(fd);}
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
      try { Promise.resolve(this.launchAssistant(view)).catch(error => new Notice("Jevos: " + error.message, 10000)); }
      catch (error) { new Notice("Jevos: " + error.message, 10000); }
    };
    const action = (kind, view, editor) => {
      try {
        const snapshot = this.captureNote(view, editor);
        Promise.resolve(kind === "classify" ? this.classifyNote(snapshot) : this.prepareText(snapshot))
          .catch(error => new Notice("Jevos: " + error.message, 10000));
      } catch (error) {new Notice("Jevos: " + error.message, 10000);}
    };
    this.addRibbonIcon("bot", "Jevos – Aktuelle Inbox-Notiz einordnen", () => action("classify"));
    this.addRibbonIcon("shield-check", "Jevos – Für KI vorbereiten", () => action("redact"));
    this.addCommand({id: "classify-active-note", name: "Aktuelle Inbox-Notiz einordnen", callback: () => action("classify")});
    this.addCommand({id: "prepare-active-text", name: "Für KI vorbereiten – Auswahl oder Notiz", callback: () => action("redact")});
    this.registerEvent(this.app.workspace.on("editor-menu", (menu, editor, view) => {
      menu.addItem(item => item.setTitle("Jevos: Einordnen").setIcon("bot").onClick(() => action("classify", view, editor)));
      menu.addItem(item => item.setTitle("Jevos: Für KI vorbereiten").setIcon("shield-check").onClick(() => action("redact", view, editor)));
    }));
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
  captureNote(providedView, providedEditor) {
    const view = providedView || this.app.workspace.getActiveViewOfType(MarkdownView);
    if (!view?.file || view.file.extension !== "md") throw new Error("Bitte eine Markdown-Notiz in Obsidian öffnen.");
    const isSource = view.getMode?.() === "source";
    const editor = providedEditor || view.editor;
    const text = isSource && editor ? editor.getValue() : view.getViewData();
    const selection = isSource && editor ? editor.getSelection() : "";
    return {view, file: view.file, source: view.file.path, title: view.file.basename,
      root: this.getRoot(), text, selection};
  }
  async connection() {
    await this.launchAssistant("inbox", {noOpen: true});
    const response = await requestUrl({url: LOCAL_URL + "/api/plugin-context", throw: false});
    if (response.status !== 200 || response.json.protocol !== 2) throw new Error("Lokalen Jevos-Dienst aktualisieren und neu starten.");
    return response.json;
  }
  async api(connection, route, data) {
    const response = await requestUrl({url: LOCAL_URL + route, method: data === undefined ? "GET" : "POST",
      headers: {"X-Session-Token": connection.token, ...(data === undefined ? {} : {"Content-Type": "application/json"})},
      ...(data === undefined ? {} : {body: JSON.stringify(data)}), throw: false});
    if (response.status !== 200) throw new Error(response.json.error || "Lokaler Dienst nicht erreichbar. Bitte erneut starten.");
    return response.json;
  }
  async classifyNote(snapshot) {
    if (this.reviewModal || this.classificationOpening) throw new Error("Ein Einordnungsdialog ist bereits geöffnet.");
    this.classificationOpening = true;
    try {
    // Check disk configuration before saving an editor outside the Inbox.
    const repo = path.resolve(this.settings.repo);
    const localConfig = path.join(repo, "config.json");
    const config = JSON.parse(fs.readFileSync(fs.existsSync(localConfig) ? localConfig : path.join(repo, "config.example.json"), "utf8").replace(/^\uFEFF/, ""));
    const inbox = path.relative(path.resolve(config.vault), path.resolve(config.inbox)).replace(/\\/g, "/");
    if (normalized(config.vault) !== normalized(snapshot.root)) throw new Error("Der lokale Assistent ist für einen anderen Vault konfiguriert.");
    if (!within(snapshot.root, snapshot.source) || !snapshot.source.startsWith(inbox + "/") || snapshot.source.slice(inbox.length + 1).includes("/"))
      throw new Error("Einordnen gilt nur für Markdown-Notizen direkt in der konfigurierten Inbox.");
    // Save through the captured Obsidian view immediately, before any startup wait.
    if (snapshot.view.file !== snapshot.file) throw new Error("Ursprüngliche Notiz nicht mehr geöffnet.");
    await snapshot.view.save(false);
    const bytes = fs.readFileSync(path.join(snapshot.root, snapshot.source));
    if (bytes.toString("utf8").replace(/^\uFEFF/, "") !== snapshot.text) throw new Error("Notiz inzwischen geändert. Bitte erneut starten.");
    snapshot.sha256 = crypto.createHash("sha256").update(bytes).digest("hex");
    const connection = await this.connection();
    if (normalized(connection.vault) !== normalized(snapshot.root)) throw new Error("Der lokale Assistent ist für einen anderen Vault konfiguriert.");
    if (!snapshot.source.startsWith(connection.inbox + "/") || snapshot.source.slice(connection.inbox.length + 1).includes("/"))
      throw new Error("Einordnen gilt nur für Markdown-Notizen direkt in der konfigurierten Inbox.");
    this.reviewModal = new ReviewNote(this, snapshot, connection); this.reviewModal.open();
    } finally {this.classificationOpening = false;}
  }
  async prepareText(snapshot) {
    const text = snapshot.selection.trim() ? snapshot.selection : snapshot.text;
    if (!text.trim()) throw new Error("Die Textauswahl beziehungsweise Notiz ist leer.");
    if (text.length > 100000) throw new Error("Maximal 100.000 Zeichen sind erlaubt.");
    const connection = await this.connection();
    const handoff = await this.api(connection, "/api/handoffs/redaction", {
      text, title: snapshot.title, kind: snapshot.selection.trim() ? "selection" : "note"});
    await this.launchAssistant("anonymize", {handoffId: handoff.handoff_id});
  }
  launchAssistant(view, options = {}) {
    if (process.platform !== "win32")
      throw new Error("Der Ein-Klick-Launcher unterstützt derzeit Windows.");
    if (!["inbox", "anonymize"].includes(view))
      throw new Error("Unbekannte Ansicht.");
    const repo = path.resolve(this.settings.repo);
    const launcher = path.join(repo, "scripts", "launch-ui.ps1");
    if (!fs.existsSync(launcher) || !fs.statSync(launcher).isFile())
      throw new Error("Launcher fehlt. GitHub-Repository aktualisieren und Plugin-Einstellungen prüfen.");
    const args = ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", launcher, "-View", view];
    if (options.noOpen) args.push("-NoOpen");
    if (options.handoffId) {
      if (view !== "anonymize" || !/^[a-f0-9]{64}$/.test(options.handoffId)) throw new Error("Ungültige Übergabe-ID.");
      args.push("-HandoffId", options.handoffId);
    }
    return new Promise((resolve, reject) => {
    const child = spawn("powershell.exe", args,
      { cwd: repo, windowsHide: true, stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    let spawnFailed = false;
    child.stderr.on("data", data => {
      // Bounded diagnostics, including parse errors before the script's catch block.
      stderr = (stderr + data.toString()).slice(-4000);
    });
    child.on("error", error => {
      spawnFailed = true;
      reject(new Error("Jevos konnte nicht gestartet werden: " + error.message));
    });
    child.on("close", code => {
      if (code !== 0 && !spawnFailed) {
        reject(new Error("Jevos konnte nicht gestartet werden (Exitcode " + code + "). " +
          (stderr.trim() || "Launcher und Python-Installation prüfen.")));
      }
      if (code === 0) resolve();
    });
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
    if (plan.backup.scope === "link-documents") this.checkDocumentBackup(plan, root);
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
  async apply(expectedBatchId) {
    const repo = path.resolve(this.settings.repo);
    const root = this.getRoot();
    if (normalized(repo) === normalized(root) || normalized(repo).startsWith(normalized(root) + path.sep))
      throw new Error("Repository muss außerhalb des Vaults liegen.");
    const base = path.join(repo, ".local", "bridge");
    const pendingFile = path.join(base, "pending.json");
    const resultFile = path.join(base, "result.json");
    if (!fs.existsSync(pendingFile)) throw new Error("Kein freigegebener Stapel vorhanden.");
    const plan = JSON.parse(fs.readFileSync(pendingFile, "utf8"));
    if (expectedBatchId && plan.batch_id !== expectedBatchId) throw new Error("Ausführungsplan wurde inzwischen ersetzt.");
    if (fs.existsSync(resultFile)) {
      const old = JSON.parse(fs.readFileSync(resultFile, "utf8"));
      if (old.batch_id === plan.batch_id) throw new Error("Dieser Stapel wurde bereits ausgeführt.");
    }
    this.preflight(plan, repo, root);
    const accepted = await new Promise(resolve => new ConfirmMoves(this.app, plan, resolve).open());
    if (!accepted) return "cancelled";
    if (plan.backup.scope === "link-documents") this.checkDocumentBackup(plan, root);
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
    return "finished";
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
  checkDocumentBackup(plan, root) {
    const entries = plan.backup.entries;
    if (!Array.isArray(entries) || !entries.length) throw new Error("Notizsicherung enthält keinen Nachweis.");
    const saved = new Map();
    for (const entry of entries) {
      if (!within(root, entry.source) || !/\.(md|canvas)$/i.test(entry.source) ||
          !/^[a-f0-9]{64}$/.test(entry.sha256) || saved.has(entry.source))
        throw new Error("Ungültiger Notizsicherungsnachweis.");
      saved.set(entry.source, entry.sha256);
      const file = path.join(root, ...entry.source.split("/"));
      if (!fs.existsSync(file) || sha(file) !== entry.sha256)
        throw new Error("Notiz seit der Sicherung geändert; bitte erneut bestätigen: " + entry.source);
    }
    for (const file of this.app.vault.getFiles()) {
      if (["md", "canvas"].includes(file.extension) && !saved.has(file.path))
        throw new Error("Neue Notiz seit der Sicherung; bitte erneut bestätigen: " + file.path);
    }
  }
};
