// Local DOM interaction checks, not a production API or accessibility audit.
// Run: JSDOM_MODULE=/absolute/path/to/jsdom node --test test_slash_command_review.cjs
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM, VirtualConsole } = require(process.env.JSDOM_MODULE || "jsdom");
const html = fs.readFileSync(path.join(__dirname, "slash-command-review.html"), "utf8");
const FULL = ["help", "status", "rename", "model", "thinking", "mode", "compact", "skills", "skill:inspection-plan"];
const AGENT = ["help", "rename", "model", "thinking", "mode", "skills", "skill:inspection-plan"];

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
    names: () => [...document.querySelectorAll("#command-list .command-name")].map((node) => node.textContent),
    disabledNames: () => [...document.querySelectorAll('#command-list [aria-disabled="true"]')].map((node) => node.dataset.name),
    values: () => [...document.querySelectorAll('#command-values [role="option"]')],
    checked: () => document.querySelector('#command-values [aria-selected="true"]')?.dataset.value ?? null,
    calls: () => JSON.parse(window.eval("JSON.stringify(demoInvocations)")),
    requests: () => JSON.parse(window.eval("JSON.stringify(demoRequests)")),
    session: () => JSON.parse(window.eval("JSON.stringify(session)")),
    resultText: () => get("result-body").textContent,
    async complete() {
      pending.splice(0).forEach((callback) => callback());
      await new Promise(setImmediate);
    }
  };
}

test("compact rows preserve catalog order; prefix filtering and ARIA agree", (t) => {
  const f = fixture(t);
  assert.deepEqual(f.names(), FULL);
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
  f.type("/rename 夜间 /巡检\n  第二行");
  f.key("Enter");
  assert.equal(f.input.value, "夜间 /巡检\n  第二行");
  assert.equal(f.input.getAttribute("role"), null);
  assert.equal(f.input.placeholder, "输入新名称");
  assert.equal(f.get("submit-button").getAttribute("aria-label"), "运行 rename");
  f.key("Enter", { shiftKey: true });
  assert.equal(f.calls().length, 0);
  f.key("Enter");
  assert.deepEqual(f.calls(), [{ name: "rename", arguments: "夜间 /巡检\n  第二行" }]);
  await f.complete();
});

test("required text arguments block execution until filled; optional Skill text does not", (t) => {
  const f = fixture(t);
  f.select("rename");
  assert.equal(f.input.hidden, false);
  assert.equal(f.get("submit-button").disabled, true);
  f.key("Enter");
  assert.equal(f.calls().length, 0);
  f.type("夜间巡检");
  assert.equal(f.get("submit-button").disabled, false);
  f.type("   ");
  assert.equal(f.get("submit-button").disabled, true);
  f.click("remove-command"); f.type("/"); f.select("skill:inspection-plan");
  assert.equal(f.input.placeholder, "补充要求（可选）");
  assert.equal(f.get("submit-button").disabled, false);
});

test("plus opens attachments without changing a message or invoking commands", (t) => {
  const f = fixture(t, "help");
  f.type("原来的消息 /保持普通字符");
  f.click("more-button");
  assert.equal(f.get("more-menu").hidden, false);
  assert.equal(f.get("command-entry"), null);
  assert.equal(f.get("attachment-entry").disabled, true);
  assert.equal(f.input.value, "原来的消息 /保持普通字符");
  f.key("Escape", {}, f.input);
  assert.equal(f.get("more-menu").hidden, true);
  assert.equal(f.calls().length, 0);
});

test("Escape closes query first, second exits; replacement Escape restores selection", (t) => {
  const f = fixture(t);
  f.type("/re"); f.key("Escape");
  assert.equal(f.get("command-palette").hidden, true);
  assert.equal(f.input.value, "/re");
  f.key("Escape");
  assert.equal(f.input.value, "");
  f.type("/rename 已有参数"); f.key("Enter");
  f.click("selected-command-name");
  f.type("/model");
  f.key("Escape");
  assert.equal(f.get("selected-command-name").textContent, "rename");
  assert.equal(f.input.value, "已有参数");
  assert.equal(f.get("command-palette").hidden, true);
});

test("replacement selection changes name; empty Backspace restores ordinary draft", (t) => {
  const f = fixture(t, "argument");
  f.click("selected-command-name");
  f.select("model");
  assert.equal(f.get("selected-command-name").textContent, "model");
  assert.equal(f.input.hidden, true);
  assert.equal(f.checked(), null);
  assert.equal(f.get("values-palette").hidden, false);
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

test("running keeps the full catalog and greys commands that cannot run; normal draft cannot submit", (t) => {
  const f = fixture(t, "running");
  assert.deepEqual(f.names(), FULL);
  assert.deepEqual(f.disabledNames(), ["model", "thinking", "mode", "compact", "skill:inspection-plan"]);
  f.select("thinking");
  assert.equal(f.get("command-chip").hidden, true);
  assert.equal(f.calls().length, 0);
  f.select("rename");
  assert.equal(f.get("selected-command-name").textContent, "rename");
  f.click("remove-command"); f.type("等待任务结束");
  assert.equal(f.get("submit-button").getAttribute("aria-label"), "停止生成");
  f.key("Enter", {}, f.input);
  assert.equal(f.get("submit-button").disabled, false);
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

test("Builtin text is shown as safe Markdown and state is refreshed from GET Session", async (t) => {
  const f = fixture(t, "argument");
  f.type('<img src=x onerror="alert(1)">'); f.click("submit-button");
  assert.equal(f.session().displayName, "园区巡检");
  await f.complete();
  const body = f.get("result-body");
  assert.equal(body.querySelector("img"), null);
  assert.match(body.querySelector("strong").textContent, /^<img/);
  assert.deepEqual(f.requests(), [
    "POST /campusclaw-service/v1/sessions/session-demo/command",
    "GET /campusclaw-service/v1/sessions/session-demo"
  ]);
  assert.equal(f.session().displayName, '<img src=x onerror="alert(1)">');
  assert.match(f.get("session-summary").textContent, /^<img/);
});

test("help result renders headings and lists from the returned text", (t) => {
  const f = fixture(t, "help");
  const body = f.get("result-body");
  assert.equal(body.querySelector("h3").textContent, "园区运维助手");
  assert.equal(body.querySelectorAll("li").length, 3);
});

test("running command focus and execution never replace the stop action", async (t) => {
  const f = fixture(t, "running");
  f.select("help");
  assert.equal(f.document.activeElement, f.get("command-run"));
  assert.equal(f.get("submit-button").getAttribute("aria-label"), "停止生成");
  f.key("Enter");
  assert.equal(f.calls().length, 1);
  assert.equal(f.get("submit-button").disabled, false);
  await f.complete();
  f.type("停止后继续"); f.click("submit-button");
  assert.equal(f.get("submit-button").disabled, true);
  assert.equal(f.input.value, "停止后继续");
  f.click("simulate-stop-terminal");
  assert.equal(f.get("submit-button").getAttribute("aria-label"), "发送消息");
  assert.equal(f.input.value, "停止后继续");
});

test("palette temporarily collapses the result and restores its disclosure choice", (t) => {
  const f = fixture(t, "help"), result = f.get("result-region");
  assert.equal(result.open, true);
  f.type("/");
  assert.equal(result.open, false);
  f.key("Escape");
  assert.equal(result.open, true);
  f.key("Escape");
  result.open = false;
  f.type("/"); f.key("Escape");
  assert.equal(result.open, false);
});

test("argumentType alone decides text input, value popup or no input", (t) => {
  const f = fixture(t);
  f.select("rename");
  assert.equal(f.input.hidden, false);
  assert.equal(f.get("values-palette").hidden, true);
  f.click("remove-command"); f.type("/"); f.select("status");
  assert.equal(f.input.hidden, true);
  assert.equal(f.get("values-palette").hidden, true);
  f.click("remove-command"); f.type("/"); f.select("thinking");
  assert.equal(f.input.hidden, true);
  assert.equal(f.get("command-palette").hidden, true);
  assert.equal(f.get("values-palette").hidden, false);
  assert.equal(f.get("command-values").getAttribute("role"), "listbox");
  assert.match(f.get("values-title").textContent, /^thinking 的可选值/);
  assert.deepEqual(f.values().map((option) => option.textContent), ["1开启", "2关闭当前"]);
});

test("value labels come from frontend copy; values without copy are shown as is", (t) => {
  const f = fixture(t);
  f.select("mode");
  assert.deepEqual(f.values().map((option) => option.textContent), ["1计划", "2实施当前"]);
  assert.deepEqual(f.values().map((option) => option.dataset.value), ["plan", "build"]);
  f.key("Escape"); f.type("/"); f.select("model");
  assert.deepEqual(f.values().map((option) => option.textContent), ["1campus-standard", "2campus-long-context"]);
  assert.deepEqual(f.requests(), [
    "GET /campusclaw-service/v1/agents/agent-demo/commands/mode/values?sessionId=session-demo",
    "GET /campusclaw-service/v1/agents/agent-demo/commands/model/values?sessionId=session-demo"
  ]);
});

test("values popup highlights the current value; arrows wrap and Enter executes", async (t) => {
  const f = fixture(t); f.select("thinking");
  const listbox = f.get("command-values");
  assert.equal(f.checked(), "off");
  assert.equal(f.document.activeElement, listbox);
  assert.equal(listbox.getAttribute("aria-activedescendant"), "value-option-1");
  f.key("ArrowDown");
  assert.equal(f.checked(), "on");
  assert.equal(listbox.getAttribute("aria-activedescendant"), "value-option-0");
  f.key("ArrowUp");
  assert.equal(f.checked(), "off");
  f.key("Home");
  assert.equal(f.checked(), "on");
  assert.equal(f.calls().length, 0);
  f.key("Enter");
  assert.deepEqual(f.calls(), [{ name: "thinking", arguments: "on" }]);
  await f.complete();
  assert.match(f.resultText(), /已开启深度思考/);
  assert.equal(f.session().thinking, "on");
  assert.equal(f.get("values-palette").hidden, true);
});

test("clicking a value or pressing its number executes right away", async (t) => {
  const f = fixture(t); f.select("mode");
  f.document.querySelector('[data-value="plan"]').click();
  assert.deepEqual(f.calls(), [{ name: "mode", arguments: "plan" }]);
  assert.equal(f.session().mode, "build");
  await f.complete();
  assert.equal(f.session().mode, "plan");
  f.type("/thinking"); f.key("Enter");
  f.key("3");
  assert.equal(f.calls().length, 1);
  f.key("1");
  assert.deepEqual(f.calls()[1], { name: "thinking", arguments: "on" });
  await f.complete();
});

test("Escape or an outside click cancels the values popup", (t) => {
  const f = fixture(t, "help");
  f.type("/thinking"); f.key("Enter", {}, f.input);
  assert.equal(f.get("values-palette").hidden, false);
  f.key("Escape");
  assert.equal(f.get("values-palette").hidden, true);
  assert.equal(f.get("command-chip").hidden, true);
  f.type("/mode"); f.key("Enter", {}, f.input);
  assert.equal(f.get("values-palette").hidden, false);
  f.document.querySelector(".timeline-inner").click();
  assert.equal(f.get("values-palette").hidden, true);
  assert.equal(f.get("command-chip").hidden, true);
  assert.equal(f.calls().length, 0);
});

test("current value that is not offered stays unhighlighted and Enter does nothing", (t) => {
  const f = fixture(t); f.select("model");
  assert.equal(f.checked(), null);
  assert.equal(f.get("command-values").getAttribute("aria-activedescendant"), null);
  assert.equal(f.document.activeElement, f.get("command-values"));
  assert.equal(f.get("submit-button").disabled, true);
  f.key("Enter");
  assert.equal(f.calls().length, 0);
  f.key("ArrowDown"); f.key("Enter");
  assert.deepEqual(f.calls(), [{ name: "model", arguments: "campus-standard" }]);
});

test("options review tab shows the popup with the current value highlighted", (t) => {
  const f = fixture(t, "options");
  assert.equal(f.get("selected-command-name").textContent, "thinking");
  assert.equal(f.checked(), "off");
  assert.equal(f.input.hidden, true);
  assert.equal(f.get("values-palette").hidden, false);
  assert.equal(f.get("submit-button").disabled, false);
});

test("an options draft is kept but cannot run while the session is running", async (t) => {
  const f = fixture(t); f.type("/mode plan"); f.key("Enter");
  assert.equal(f.checked(), "plan");
  f.window.eval("running = true; render()");
  assert.equal(f.checked(), null);
  assert.equal(f.values().every((option) => option.getAttribute("aria-disabled") === "true"), true);
  assert.equal(f.get("command-run").hidden, false);
  assert.equal(f.get("command-run").disabled, true);
  assert.equal(f.get("inline-error").textContent, "任务运行中不可执行，草稿已保留");
  f.document.querySelector('[data-value="build"]').click();
  f.click("command-run");
  assert.equal(f.calls().length, 0);
  f.window.eval("running = false; render()");
  assert.equal(f.checked(), "plan");
  f.click("submit-button"); await f.complete();
  assert.deepEqual(f.calls(), [{ name: "mode", arguments: "plan" }]);
});

test("typed value outside the options falls back to the current value", (t) => {
  const f = fixture(t); f.type("/mode PLAN"); f.select("mode");
  assert.equal(f.checked(), "build"); assert.equal(f.input.hidden, true);
  assert.equal(f.get("submit-button").disabled, false); assert.equal(f.calls().length, 0);
});

test("complete mode name selects mode despite the model prefix", (t) => {
  const f = fixture(t); f.type("/mode plan"); f.key("Enter");
  assert.equal(f.get("selected-command-name").textContent, "mode");
  assert.equal(f.checked(), "plan"); assert.equal(f.calls().length, 0);
});

test("new chat lists Agent commands, reads initial values and creates the session before executing", async (t) => {
  const f = fixture(t, "newChat");
  assert.deepEqual(f.names(), AGENT);
  assert.equal(f.get("session-summary").textContent, "新对话 · 尚未创建会话");
  assert.equal(f.get("empty-chat").hidden, false);
  f.select("thinking");
  assert.equal(f.checked(), "on");
  f.key("2");
  assert.deepEqual(f.calls(), [{ name: "thinking", arguments: "off" }]);
  await f.complete();
  assert.deepEqual(f.requests(), [
    "GET /campusclaw-service/v1/agents/agent-demo/commands/thinking/values",
    "POST /campusclaw-service/v1/sessions",
    "POST /campusclaw-service/v1/sessions/session-new/command",
    "GET /campusclaw-service/v1/sessions/session-new"
  ]);
  assert.match(f.resultText(), /已关闭深度思考/);
  assert.match(f.get("session-summary").textContent, /^新对话 · campus-standard · 深度思考关闭 · 实施模式$/);
  assert.equal(f.get("empty-chat").hidden, false);
  f.type("/");
  assert.deepEqual(f.names(), FULL);
  f.select("help"); f.click("submit-button"); await f.complete();
  assert.equal(f.requests().filter((request) => request === "POST /campusclaw-service/v1/sessions").length, 1);
});
