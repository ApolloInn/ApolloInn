/**
 * Auto Setup — 首次启动时自动配置 9router。
 *
 * 做的事情：
 * 1. 创建 OpenAI Compatible provider node（指向 gateway-server）
 * 2. 创建 connection（用 usertoken 作为 API key）
 * 3. 注册 Kiro 模型别名
 * 4. 创建 combo 映射（kiro-opus-4-6 -> claude-opus-4.6 等）
 *
 * 用户只需提供 usertoken 和网关地址。
 */

const KIRO_MODELS = [
  { id: "claude-sonnet-4.5", name: "Claude Sonnet 4.5" },
  { id: "claude-opus-4.5", name: "Claude Opus 4.5" },
  { id: "claude-opus-4.6", name: "Claude Opus 4.6" },
  { id: "claude-sonnet-4", name: "Claude Sonnet 4" },
  { id: "claude-haiku-4.5", name: "Claude Haiku 4.5" },
  { id: "claude-3.7-sonnet", name: "Claude 3.7 Sonnet" },
  { id: "auto", name: "Auto" },
];

// Combo 映射：用户友好名 -> 实际 Kiro 模型名
const COMBO_MAPPINGS = [
  {
    name: "kiro-opus-4-6",
    models: ["claude-opus-4.6"],
  },
  {
    name: "kiro-opus-4-5",
    models: ["claude-opus-4.5"],
  },
  {
    name: "kiro-sonnet-4-5",
    models: ["claude-sonnet-4.5"],
  },
  {
    name: "kiro-sonnet-4",
    models: ["claude-sonnet-4"],
  },
  {
    name: "kiro-haiku-4-5",
    models: ["claude-haiku-4.5"],
  },
  {
    name: "kiro-auto",
    models: ["auto"],
  },
];

/**
 * 执行自动配置。
 *
 * @param {string} baseUrl - 本地 9router 的 API 地址，如 http://localhost:3000
 * @param {string} gatewayUrl - 网关服务器公网地址，如 https://gw.example.com
 * @param {string} usertoken - 管理员分配的 usertoken
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function autoSetup(baseUrl, gatewayUrl, usertoken) {
  try {
    const api = (path, opts = {}) =>
      fetch(`${baseUrl}/api${path}`, {
        ...opts,
        headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      }).then((r) => r.json());

    // 1. 检查是否已配置过
    const nodesRes = await api("/provider-nodes");
    const existingNode = (nodesRes.nodes || []).find(
      (n) => n.name === "Kiro Gateway"
    );

    let nodeId;

    if (existingNode) {
      nodeId = existingNode.id;
      console.log("[auto-setup] Kiro Gateway node already exists:", nodeId);
    } else {
      // 创建 OpenAI Compatible provider node
      const nodeRes = await api("/provider-nodes", {
        method: "POST",
        body: JSON.stringify({
          name: "Kiro Gateway",
          prefix: "kiro-gw",
          apiType: "chat",
          baseUrl: `${gatewayUrl}/v1`,
          type: "openai-compatible",
        }),
      });

      if (nodeRes.error) throw new Error(`Create node failed: ${nodeRes.error}`);
      nodeId = nodeRes.node.id;
      console.log("[auto-setup] Created provider node:", nodeId);
    }

    // 2. 创建 connection（如果不存在）
    const connsRes = await api("/providers");
    const existingConn = (connsRes.connections || []).find(
      (c) => c.provider === nodeId
    );

    if (!existingConn) {
      const connRes = await api("/providers", {
        method: "POST",
        body: JSON.stringify({
          provider: nodeId,
          apiKey: usertoken,
          name: "Kiro Gateway",
          priority: 1,
        }),
      });
      if (connRes.error) throw new Error(`Create connection failed: ${connRes.error}`);
      console.log("[auto-setup] Created connection");
    } else {
      console.log("[auto-setup] Connection already exists");
    }

    // 3. 注册模型别名
    for (const model of KIRO_MODELS) {
      const fullModel = `${nodeId}/${model.id}`;
      await api("/models/alias", {
        method: "PUT",
        body: JSON.stringify({ alias: model.id, model: fullModel }),
      });
    }
    console.log("[auto-setup] Model aliases registered:", KIRO_MODELS.length);

    // 4. 创建 combo 映射
    for (const combo of COMBO_MAPPINGS) {
      const comboModels = combo.models.map((m) => `${nodeId}/${m}`);
      try {
        await api("/combos", {
          method: "POST",
          body: JSON.stringify({ name: combo.name, models: comboModels }),
        });
      } catch (e) {
        // combo 可能已存在，忽略
      }
    }
    console.log("[auto-setup] Combos created:", COMBO_MAPPINGS.length);

    return { success: true };
  } catch (e) {
    console.error("[auto-setup] Failed:", e);
    return { success: false, error: e.message };
  }
}

export { KIRO_MODELS, COMBO_MAPPINGS };
