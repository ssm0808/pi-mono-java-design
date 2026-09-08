// Local DOM interaction checks, not a production API or accessibility audit.
// Run: JSDOM_MODULE=/absolute/path/to/jsdom node --test test_slash_command_review.cjs
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM, VirtualConsole } = require(process.env.JSDOM_MODULE || "jsdom");
const html = fs.readFileSync(path.join(__dirname, "slash-command-review.html"), "utf8");

function fixture(t, state = "catalog") {
  const errors = [], pending = [];
  let networkCalls = 0;
  const virtualConsole = new VirtualConsole();
  virtualConsole.on("jsdomError", (error) => errors.push(error));
  const dom = new JSDOM(html, {
    runScripts: "dangerously", url: "http://localhost/slash-command-review.html#" + state, virtualConsole,
    beforeParse(window) {
      const blocked = () => { networkCalls++; throw new Error("Review must not call network APIs"); };
      window.fetch = blocked; window.XMLHttpRequest = blocked;
      window.WebSocket = blocked; window.EventSource = blocked;
      window.setTimeout = (callback) => { pending.push(callback); return pending.length; };
    }
  });
  const { window } = dom;
  const { document } = window;
  const get = (id) => document.getElementById(id);
  const input = get("composer-input");
  const key = (key, options = {}, element = document.activeElement === document.body ? input : document.activeElement) =>
    element.dispatchEvent(new window.KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...options }));
  t.after(() => {
    assert.deepEqual(errors, []);
    assert.equal(networkCalls, 0);
    dom.window.close();
  });
  return {
    window, document, get, input, key,
    click: (id) => get(id).click(),
    type(value) {
      input.focus(); input.value = value;
      input.dispatchEvent(new window.Event("input", { bubbles: true }));
    },
    select(name) { document.querySelector('[data-name="' + name + '"]').click(); },
    state(name) { document.querySelector('[data-state="' + name + '"]').click(); },
    names: () => [...document.querySelectorAll(".command-name")].map((node) => node.textContent),
    calls: () => JSON.parse(window.eval("JSON.stringify(demoInvocations)")),
    async complete() {
      pending.splice(0).forEach((callback) => callback());
      await new Promise(setImmediate);
    }
  };
}

test("compact rows preserve catalog order; prefix filtering and ARIA agree", (t) => {
  const f = fixture(t);
  assert.deepEqual(f.names(), ["help", "status", "name", "model", "thinking", "compact", "skills", "skill:inspection-plan"]);
  assert.equal(f.document.querySelector(".kind-badge, .palette-head, .mode-line, .slash-icon"), null);
  f.type("/s");
  assert.deepEqual(f.names(), ["status", "skills", "skill:inspection-plan"]);
  assert.equal(f.input.getAttribute("aria-activedescendant"), "command-option-0");
  f.key("End");
  assert.equal(f.input.getAttribute("aria-activedescendant"), "command-option-2");
  assert.equal(f.document.querySelector('[aria-selected="true"][role="option"]').dataset.name, "skill:inspection-plan");
  f.type("/S");
  assert.deepEqual(f.names(), []);
  assert.equal(f.get("submit-button").disabled, true);
});

test("selection closes palette; no-input hides textarea and needs a new submission", async (t) => {
  const f = fixture(t);
  f.input.focus();
  assert.equal(f.get("submit-button").disabled, true);
  f.click("submit-button");
  assert.equal(f.calls().length, 0);
  f.key("Enter");
  assert.equal(f.get("command-palette").hidden, true);
  assert.equal(f.get("selected-command-name").textContent, "help");
  assert.equal(f.input.hidden, true);
  assert.equal(f.document.activeElement, f.get("submit-button"));
  assert.equal(f.calls().length, 0);
  f.key("Enter", { repeat: true });
  assert.equal(f.calls().length, 0);
  f.key("Enter");
  f.click("submit-button");
  assert.equal(f.calls().length, 1);
  assert.equal(f.get("submit-button").disabled, true);
  await f.complete();
  assert.equal(f.get("result-region").classList.contains("visible"), true);
  assert.equal(f.get("command-chip").hidden, true);
});

test("parameters remain separate and preserve text, slash and line breaks", async (t) => {
  const f = fixture(t);
  f.type("/name 夜间 /巡检\n  第二行");
  f.key("Enter");
  assert.equal(f.input.value, "夜间 /巡检\n  第二行");
  assert.equal(f.input.getAttribute("role"), null);
  assert.equal(f.input.placeholder, "[displayName]");
  assert.equal(f.get("submit-button").getAttribute("aria-label"), "运行 name");
  f.key("Enter", { shiftKey: true });
  assert.equal(f.calls().length, 0);
  f.key("Enter");
  assert.deepEqual(f.calls(), [{ name: "name", arguments: "夜间 /巡检\n  第二行" }]);
  await f.complete();
});

test("plus entry suspends and restores message on cancel and success", async (t) => {
  const f = fixture(t, "help");
  f.type("原来的消息 /保持普通字符");
  assert.equal(f.get("command-palette").hidden, true);
  f.click("more-button");
  assert.equal(f.get("more-menu").hidden, false);
  assert.equal(f.document.activeElement, f.get("command-entry"));
  f.click("command-entry");
  f.select("name");
  f.type("另一个名称");
  f.click("remove-command");
  assert.equal(f.input.value, "原来的消息 /保持普通字符");
  f.click("more-button"); f.click("command-entry");
  f.select("help"); f.click("submit-button");
  await f.complete();
  assert.equal(f.input.value, "原来的消息 /保持普通字符");
  assert.equal(f.document.querySelectorAll(".message.user").length, 1);
});

test("Escape closes query first, second exits; replacement Escape restores selection", (t) => {
  const f = fixture(t);
  f.type("/na"); f.key("Escape");
  assert.equal(f.get("command-palette").hidden, true);
  assert.equal(f.input.value, "/na");
  f.key("Escape");
  assert.equal(f.input.value, "");
  f.type("/name 已有参数"); f.key("Enter");
  f.click("selected-command-name");
  f.type("/model");
  f.key("Escape");
  assert.equal(f.get("selected-command-name").textContent, "name");
  assert.equal(f.input.value, "已有参数");
  assert.equal(f.get("command-palette").hidden, true);
});

test("replacement selection changes name; empty Backspace restores ordinary draft", (t) => {
  const f = fixture(t, "argument");
  f.click("selected-command-name");
  f.select("model");
  assert.equal(f.get("selected-command-name").textContent, "model");
  assert.equal(f.input.value, "");
  assert.equal(f.input.placeholder, "[modelId]");
  f.key("Backspace");
  assert.equal(f.get("command-chip").hidden, true);
  assert.equal(f.input.value, "");
  f.type("/");
  f.select("help");
  f.key("Backspace");
  assert.equal(f.get("command-chip").hidden, true);
});

test("unknown commands and no-input arguments are never silently sent or dropped", (t) => {
  const f = fixture(t, "unmatched");
  f.input.focus();
  f.key("Enter"); f.click("submit-button");
  assert.equal(f.input.value, "/deploy tomorrow");
  assert.equal(f.calls().length, 0);
  assert.equal(f.document.querySelectorAll(".message.user").length, 1);
  f.type("/help surprise"); f.key("Enter");
  assert.equal(f.get("command-chip").hidden, true);
  assert.equal(f.input.value, "/help surprise");
  assert.equal(f.get("inline-error").textContent, "此命令不接收参数");
});

test("IME and repeated Enter cannot select or run a command", (t) => {
  const f = fixture(t);
  f.input.focus();
  f.key("Enter", { isComposing: true });
  f.key("Enter", { keyCode: 229 });
  f.key("Enter", { repeat: true });
  assert.equal(f.get("command-chip").hidden, true);
  f.input.dispatchEvent(new f.window.CompositionEvent("compositionstart", { bubbles: true }));
  f.key("Enter");
  assert.equal(f.get("command-chip").hidden, true);
  f.input.dispatchEvent(new f.window.CompositionEvent("compositionend", { bubbles: true }));
  f.key("Enter");
  assert.equal(f.get("command-chip").hidden, false);
  assert.equal(f.calls().length, 0);
});

test("running fixture omits unavailable commands and input; normal draft cannot submit", (t) => {
  const f = fixture(t, "running");
  assert.deepEqual(f.names(), ["help", "status", "name", "model", "thinking", "skills"]);
  f.select("model");
  assert.equal(f.input.hidden, true);
  assert.equal(f.get("submit-button").disabled, false);
  f.click("remove-command"); f.type("等待任务结束");
  assert.equal(f.get("submit-button").disabled, true);
});

test("Skill gate and oversized arguments preserve draft without invoking mock executor", (t) => {
  const f = fixture(t);
  f.select("skill:inspection-plan"); f.type("整理巡检"); f.click("submit-button");
  assert.equal(f.input.value, "整理巡检");
  assert.equal(f.get("inline-error").textContent, "当前暂不支持运行该命令");
  assert.equal(f.calls().length, 0);
  f.state("argument"); f.type("😀".repeat(2049)); f.click("submit-button");
  assert.equal(f.get("inline-error").textContent, "参数最多 2048 个字符");
  assert.equal(f.calls().length, 0);
});

test("review tabs retain open palette and invalidate pending mock completion", async (t) => {
  const f = fixture(t, "help");
  f.state("catalog");
  assert.equal(f.get("command-palette").hidden, false);
  f.select("help"); f.click("submit-button");
  f.state("unmatched");
  await f.complete();
  assert.equal(f.input.value, "/deploy tomorrow");
  assert.equal(f.get("result-region").classList.contains("visible"), false);
});

test("result data is rendered as plain text", async (t) => {
  const f = fixture(t, "argument");
  f.type('<img src=x onerror="alert(1)">'); f.click("submit-button");
  await f.complete();
  assert.equal(f.document.querySelector(".help-description img"), null);
  assert.match(f.document.querySelector(".help-description").textContent, /<img/);
});
