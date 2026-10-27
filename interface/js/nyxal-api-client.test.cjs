"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "nyxal-api-client.js"), "utf8");

function loadClient({ base, fetchImpl } = {}) {
  const window = {};
  if (base !== undefined) window.NYXAL_API_BASE = base;

  const calls = [];
  const effectiveFetch = fetchImpl || (async () => ({
    ok: true,
    status: 200,
    json: async () => ({ sucesso: true }),
    text: async () => "ok",
    blob: async () => ({ tipo: "blob-fixture" }),
  }));

  vm.runInNewContext(source, {
    window,
    fetch: async (url, options) => {
      calls.push({ url, options });
      return effectiveFetch(url, options);
    },
  });

  return { window, post: window.nyxalApiPost, calls };
}

test("uses the configured base URL and forwards POST options", async () => {
  const response = {
    ok: true,
    status: 200,
    json: async () => ({ sucesso: true }),
  };
  const client = loadClient({
    base: "http://nyxal.local/",
    fetchImpl: async () => response,
  });
  const signal = { abortRequested: false };
  const headers = { "Content-Type": "application/json" };
  const body = JSON.stringify({ mensagem: "teste" });

  const result = await client.post("/api/chat", { body, headers, signal });

  assert.equal(client.calls.length, 1);
  assert.equal(client.calls[0].url, "http://nyxal.local/api/chat");
  assert.equal(client.calls[0].options.method, "POST");
  assert.equal(client.calls[0].options.body, body);
  assert.deepEqual(client.calls[0].options.headers, headers);
  assert.strictEqual(client.calls[0].options.signal, signal);
  assert.strictEqual(result.response, response);
  assert.deepEqual(result.data, { sucesso: true });
});

test("falls back to the local API base when no override is configured", async () => {
  const client = loadClient();

  await client.post("/api/status");

  assert.equal(client.calls[0].url, "http://127.0.0.1:8010/api/status");
});

test("supports text and blob response modes", async () => {
  const response = {
    ok: true,
    status: 200,
    json: async () => ({ unused: true }),
    text: async () => "resposta textual",
    blob: async () => ({ tipo: "imagem-fixture" }),
  };
  const client = loadClient({ fetchImpl: async () => response });

  const textResult = await client.post("/api/text", { parse: "text" });
  const blobResult = await client.post("/api/blob", { parse: "blob" });

  assert.equal(textResult.data, "resposta textual");
  assert.deepEqual(blobResult.data, { tipo: "imagem-fixture" });
});

test("treats malformed JSON as null for successful responses", async () => {
  const client = loadClient({
    fetchImpl: async () => ({
      ok: true,
      status: 200,
      json: async () => { throw new SyntaxError("JSON inválido"); },
    }),
  });

  const result = await client.post("/api/legacy");

  assert.equal(result.data, null);
});

test("throws a structured error for non-OK responses by default", async () => {
  const response = {
    ok: false,
    status: 422,
    json: async () => ({ motivo: "entrada_invalida" }),
  };
  const client = loadClient({ fetchImpl: async () => response });

  await assert.rejects(
    client.post("/api/action"),
    (error) => {
      assert.equal(error.status, 422);
      assert.deepEqual(error.payload, { motivo: "entrada_invalida" });
      assert.match(error.message, /Nyxal API POST \/api\/action: entrada_invalida/);
      return true;
    },
  );
});

test("supports non-throwing error handling when explicitly requested", async () => {
  const response = {
    ok: false,
    status: 503,
    json: async () => ({ erro: "servico_indisponivel" }),
  };
  const client = loadClient({ fetchImpl: async () => response });

  const result = await client.post("/api/optional", { throwOnError: false });

  assert.strictEqual(result.response, response);
  assert.deepEqual(result.data, { erro: "servico_indisponivel" });
});
