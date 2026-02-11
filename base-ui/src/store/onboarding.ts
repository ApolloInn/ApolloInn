import { create } from "zustand";

// ─── Provider & Model Catalog ───

export type ModelCapability = "chat" | "code" | "reasoning" | "vision" | "embedding";

export interface ModelInfo {
  id: string;
  name: string;
  contextWindow: number;
  capabilities: ModelCapability[];
  recommended?: boolean;
  description: string;
}

export interface ProviderInfo {
  id: string;
  name: string;
  icon: string;
  description: string;
  apiKeyPrefix: string;
  apiKeyPlaceholder: string;
  apiKeyHint: string;
  models: ModelInfo[];
}

// 完整模型目录 — 同步 router.ts + openclaw-main (2026-02)
export const PROVIDER_CATALOG: ProviderInfo[] = [
  // ─── 主流云端提供方 ────────────────────────────
  {
    id: "anthropic",
    name: "Anthropic Claude",
    icon: "psychology",
    description: "",
    apiKeyPrefix: "sk-ant-",
    apiKeyPlaceholder: "sk-ant-api03-...",
    apiKeyHint: "从 console.anthropic.com 获取",
    models: [
      { id: "claude-opus-4-6-20260203", name: "Claude Opus 4.6", contextWindow: 1000000, capabilities: ["chat", "code", "reasoning", "vision"], description: "旗舰，百万上下文" },
      { id: "claude-sonnet-4-5-20250514", name: "Claude Sonnet 4.5", contextWindow: 200000, capabilities: ["chat", "code", "reasoning", "vision"], recommended: true, description: "性能与成本最佳平衡" },
      { id: "claude-haiku-3-5-20241022", name: "Claude Haiku 3.5", contextWindow: 200000, capabilities: ["chat", "code", "vision"], recommended: true, description: "极速响应、低成本" },
    ],
  },
  {
    id: "openai",
    name: "OpenAI",
    icon: "auto_awesome",
    description: "",
    apiKeyPrefix: "sk-",
    apiKeyPlaceholder: "sk-proj-...",
    apiKeyHint: "从 platform.openai.com 获取",
    models: [
      { id: "gpt-5.2", name: "GPT-5.2", contextWindow: 400000, capabilities: ["chat", "code", "reasoning", "vision"], recommended: true, description: "最新旗舰" },
      { id: "gpt-5.1-codex", name: "GPT-5.1 Codex", contextWindow: 400000, capabilities: ["code", "reasoning", "vision"], description: "专业编程" },
      { id: "o4-mini", name: "o4-mini", contextWindow: 200000, capabilities: ["chat", "code", "reasoning", "vision"], recommended: true, description: "深度推理" },
      { id: "gpt-5-mini", name: "GPT-5 Mini", contextWindow: 400000, capabilities: ["chat", "code", "vision"], description: "高性价比" },
      { id: "gpt-5.1-codex-mini", name: "GPT-5.1 Codex Mini", contextWindow: 400000, capabilities: ["code", "vision"], description: "轻量编程" },
      { id: "gpt-4o", name: "GPT-4o", contextWindow: 128000, capabilities: ["chat", "code", "vision"], description: "经典多模态" },
      { id: "gpt-4o-mini", name: "GPT-4o Mini", contextWindow: 128000, capabilities: ["chat", "vision"], recommended: true, description: "最低成本" },
      { id: "gpt-4.1", name: "GPT-4.1", contextWindow: 1047576, capabilities: ["chat", "code", "vision"], description: "百万上下文" },
      { id: "gpt-4.1-mini", name: "GPT-4.1 Mini", contextWindow: 1047576, capabilities: ["chat", "code", "vision"], description: "百万上下文轻量" },
      { id: "o3", name: "o3", contextWindow: 200000, capabilities: ["chat", "code", "reasoning", "vision"], description: "推理旗舰" },
    ],
  },
  {
    id: "google",
    name: "Google Gemini",
    icon: "neurology",
    description: "",
    apiKeyPrefix: "AIza",
    apiKeyPlaceholder: "AIzaSy...",
    apiKeyHint: "从 aistudio.google.com 获取",
    models: [
      { id: "gemini-3-pro-preview", name: "Gemini 3 Pro", contextWindow: 1048576, capabilities: ["chat", "code", "reasoning", "vision"], description: "最新旗舰" },
      { id: "gemini-3-flash-preview", name: "Gemini 3 Flash", contextWindow: 1048576, capabilities: ["chat", "code", "reasoning", "vision"], recommended: true, description: "速度与质量兼备" },
      { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", contextWindow: 1048576, capabilities: ["chat", "code", "reasoning", "vision"], description: "成熟稳定" },
      { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", contextWindow: 1048576, capabilities: ["chat", "code", "reasoning", "vision"], recommended: true, description: "高性价比" },
      { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", contextWindow: 1048576, capabilities: ["chat", "vision"], description: "超低成本" },
    ],
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    icon: "explore",
    description: "",
    apiKeyPrefix: "sk-",
    apiKeyPlaceholder: "sk-...",
    apiKeyHint: "从 platform.deepseek.com 获取",
    models: [
      { id: "deepseek-chat", name: "DeepSeek V3.2 Chat", contextWindow: 128000, capabilities: ["chat", "code"], recommended: true, description: "通用对话" },
      { id: "deepseek-reasoner", name: "DeepSeek V3.2 Reasoner", contextWindow: 128000, capabilities: ["chat", "code", "reasoning"], recommended: true, description: "深度推理" },
    ],
  },

  // ─── NVIDIA NIM（免费聚合平台）────────────────
  {
    id: "nvidia",
    name: "NVIDIA NIM",
    icon: "developer_board",
    description: "",
    apiKeyPrefix: "nvapi-",
    apiKeyPlaceholder: "nvapi-...",
    apiKeyHint: "从 build.nvidia.com 获取（免费）",
    models: [
      { id: "qwen/qwen3-235b-a22b", name: "Qwen3 235B (MoE)", contextWindow: 131072, capabilities: ["chat", "code", "reasoning"], description: "旗舰 MoE" },
      { id: "qwen/qwen3-coder-480b-a35b-instruct", name: "Qwen3 Coder 480B", contextWindow: 262144, capabilities: ["code", "reasoning"], description: "代码旗舰" },
      { id: "qwen/qwen3-next-80b-a3b-instruct", name: "Qwen3-Next 80B", contextWindow: 262144, capabilities: ["chat", "code", "reasoning"], recommended: true, description: "综合最优" },
      { id: "qwen/qwen3-next-80b-a3b-thinking", name: "Qwen3-Next 80B Thinking", contextWindow: 131072, capabilities: ["chat", "code", "reasoning"], description: "推理增强" },
      { id: "qwen/qwq-32b", name: "QwQ-32B", contextWindow: 131072, capabilities: ["chat", "code", "reasoning"], description: "深度推理" },
      { id: "qwen/qwen2.5-coder-32b-instruct", name: "Qwen2.5 Coder 32B", contextWindow: 32768, capabilities: ["code"], description: "经典编程" },
      { id: "moonshotai/kimi-k2-instruct-0905", name: "Kimi K2 0905", contextWindow: 131072, capabilities: ["chat", "code"], description: "最快版 K2" },
      { id: "moonshotai/kimi-k2-instruct", name: "Kimi K2", contextWindow: 131072, capabilities: ["chat", "code"], description: "通用 K2" },
      { id: "moonshotai/kimi-k2-thinking", name: "Kimi K2 Thinking", contextWindow: 131072, capabilities: ["chat", "code", "reasoning"], description: "深度推理" },
      { id: "moonshotai/kimi-k2.5", name: "Kimi K2.5", contextWindow: 262144, capabilities: ["chat", "code", "reasoning", "vision"], recommended: true, description: "1T MoE 多模态" },
      { id: "minimaxai/minimax-m2", name: "MiniMax M2", contextWindow: 128000, capabilities: ["chat", "code", "reasoning"], description: "230B MoE" },
      { id: "minimaxai/minimax-m2.1", name: "MiniMax M2.1", contextWindow: 128000, capabilities: ["chat", "code", "reasoning"], recommended: true, description: "最快首字" },
      { id: "nvidia/llama-3.1-nemotron-ultra-253b-v1", name: "Nemotron Ultra 253B", contextWindow: 131072, capabilities: ["chat", "code", "reasoning"], description: "NVIDIA 自研" },
      { id: "nvidia/nemotron-3-nano-30b-a3b", name: "Nemotron 3 Nano 30B", contextWindow: 1048576, capabilities: ["chat", "code", "reasoning"], description: "百万上下文" },
      { id: "meta/llama-3.3-70b-instruct", name: "Llama 3.3 70B", contextWindow: 128000, capabilities: ["chat", "code"], description: "Meta 开源" },
      { id: "deepseek-ai/deepseek-r1", name: "DeepSeek R1 (NIM)", contextWindow: 65536, capabilities: ["chat", "reasoning"], description: "推理模型" },
      { id: "deepseek-ai/deepseek-v3.2", name: "DeepSeek V3.2 (NIM)", contextWindow: 163840, capabilities: ["chat", "code"], description: "通用模型" },
      { id: "nvidia/nemotron-nano-12b-v2-vl", name: "Nemotron Nano 12B VL", contextWindow: 128000, capabilities: ["chat", "vision"], description: "视觉语言" },
    ],
  },

  // ─── 国产提供方 ────────────────────────────────
  {
    id: "moonshot",
    name: "Moonshot Kimi",
    icon: "dark_mode",
    description: "",
    apiKeyPrefix: "sk-",
    apiKeyPlaceholder: "sk-...",
    apiKeyHint: "从 platform.moonshot.cn 获取",
    models: [
      { id: "kimi-k2.5", name: "Kimi K2.5", contextWindow: 256000, capabilities: ["chat", "code", "reasoning"], recommended: true, description: "256K 上下文" },
      { id: "kimi-k2", name: "Kimi K2", contextWindow: 131072, capabilities: ["chat", "code"], description: "通用模型" },
    ],
  },
  {
    id: "qwen",
    name: "阿里通义千问",
    icon: "cloud",
    description: "",
    apiKeyPrefix: "sk-",
    apiKeyPlaceholder: "sk-...",
    apiKeyHint: "从 dashscope.console.aliyun.com 获取",
    models: [
      { id: "qwen3-235b-a22b", name: "Qwen3 235B", contextWindow: 131072, capabilities: ["chat", "code", "reasoning"], recommended: true, description: "旗舰 MoE" },
      { id: "qwen3-32b", name: "Qwen3 32B", contextWindow: 131072, capabilities: ["chat", "code", "reasoning"], description: "平衡之选" },
      { id: "qwen3-coder", name: "Qwen3 Coder", contextWindow: 262144, capabilities: ["code", "reasoning"], description: "代码专精" },
      { id: "qwq-32b", name: "QwQ 32B", contextWindow: 131072, capabilities: ["chat", "reasoning"], description: "推理专用" },
      { id: "qwen-vl-max", name: "Qwen VL Max", contextWindow: 131072, capabilities: ["chat", "vision"], description: "视觉理解" },
    ],
  },
  {
    id: "zhipu",
    name: "智谱 GLM",
    icon: "school",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "your-api-key",
    apiKeyHint: "从 open.bigmodel.cn 获取",
    models: [
      { id: "glm-4.7", name: "GLM-4.7", contextWindow: 198000, capabilities: ["chat", "code", "reasoning"], recommended: true, description: "最新旗舰" },
      { id: "glm-4.6", name: "GLM-4.6", contextWindow: 198000, capabilities: ["chat", "code"], description: "高性能" },
      { id: "glm-4.5", name: "GLM-4.5", contextWindow: 128000, capabilities: ["chat", "code"], description: "稳定版" },
    ],
  },
  {
    id: "minimax",
    name: "MiniMax",
    icon: "hub",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "your-api-key",
    apiKeyHint: "从 platform.minimaxi.com 获取",
    models: [
      { id: "MiniMax-M2.1", name: "MiniMax M2.1", contextWindow: 200000, capabilities: ["chat", "code", "reasoning"], recommended: true, description: "最快首字" },
      { id: "MiniMax-VL-01", name: "MiniMax VL 01", contextWindow: 200000, capabilities: ["chat", "vision"], description: "视觉模型" },
    ],
  },
  {
    id: "xiaomi",
    name: "小米 MiMo",
    icon: "phone_android",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "your-api-key",
    apiKeyHint: "从小米开放平台获取",
    models: [
      { id: "mimo-v2-flash", name: "MiMo V2 Flash", contextWindow: 262144, capabilities: ["chat", "code"], recommended: true, description: "262K 上下文" },
    ],
  },

  // ─── 聚合/代理平台 ────────────────────────────
  {
    id: "venice",
    name: "Venice AI",
    icon: "shield",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "your-api-key",
    apiKeyHint: "从 venice.ai 获取（隐私优先）",
    models: [
      { id: "llama-3.3-70b", name: "Llama 3.3 70B", contextWindow: 131072, capabilities: ["chat", "code"], recommended: true, description: "私密推理" },
      { id: "qwen3-235b-a22b-thinking-2507", name: "Qwen3 235B Thinking", contextWindow: 131072, capabilities: ["chat", "code", "reasoning"], description: "私密推理" },
      { id: "qwen3-coder-480b-a35b-instruct", name: "Qwen3 Coder 480B", contextWindow: 262144, capabilities: ["code", "reasoning"], description: "私密编程" },
      { id: "qwen3-next-80b", name: "Qwen3 Next 80B", contextWindow: 262144, capabilities: ["chat", "code"], description: "私密通用" },
      { id: "qwen3-vl-235b-a22b", name: "Qwen3 VL 235B", contextWindow: 262144, capabilities: ["chat", "vision"], description: "私密视觉" },
      { id: "deepseek-v3.2", name: "DeepSeek V3.2", contextWindow: 163840, capabilities: ["chat", "code", "reasoning"], description: "私密推理" },
      { id: "zai-org-glm-4.7", name: "GLM 4.7", contextWindow: 202752, capabilities: ["chat", "code", "reasoning"], description: "智谱旗舰" },
      { id: "openai-gpt-oss-120b", name: "GPT OSS 120B", contextWindow: 131072, capabilities: ["chat", "code"], description: "OpenAI 开源" },
      { id: "claude-opus-45", name: "Claude Opus 4.5 (匿名)", contextWindow: 202752, capabilities: ["chat", "code", "reasoning", "vision"], description: "经 Venice 代理" },
      { id: "openai-gpt-52", name: "GPT-5.2 (匿名)", contextWindow: 262144, capabilities: ["chat", "code", "reasoning"], description: "经 Venice 代理" },
      { id: "grok-41-fast", name: "Grok 4.1 Fast (匿名)", contextWindow: 262144, capabilities: ["chat", "code", "reasoning", "vision"], description: "经 Venice 代理" },
    ],
  },
  {
    id: "synthetic",
    name: "Synthetic",
    icon: "token",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "your-api-key",
    apiKeyHint: "从 synthetic.new 获取（免费聚合）",
    models: [
      { id: "hf:MiniMaxAI/MiniMax-M2.1", name: "MiniMax M2.1", contextWindow: 192000, capabilities: ["chat", "code"], recommended: true, description: "免费" },
      { id: "hf:moonshotai/Kimi-K2-Thinking", name: "Kimi K2 Thinking", contextWindow: 256000, capabilities: ["chat", "code", "reasoning"], description: "免费推理" },
      { id: "hf:zai-org/GLM-4.7", name: "GLM-4.7", contextWindow: 198000, capabilities: ["chat", "code", "reasoning"], description: "免费" },
      { id: "hf:deepseek-ai/DeepSeek-R1-0528", name: "DeepSeek R1", contextWindow: 128000, capabilities: ["chat", "reasoning"], description: "免费推理" },
      { id: "hf:deepseek-ai/DeepSeek-V3.2", name: "DeepSeek V3.2", contextWindow: 159000, capabilities: ["chat", "code"], description: "免费" },
      { id: "hf:meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", name: "Llama 4 Maverick", contextWindow: 524000, capabilities: ["chat", "code"], description: "524K 上下文" },
      { id: "hf:Qwen/Qwen3-235B-A22B-Instruct-2507", name: "Qwen3 235B", contextWindow: 256000, capabilities: ["chat", "code"], description: "免费" },
      { id: "hf:Qwen/Qwen3-Coder-480B-A35B-Instruct", name: "Qwen3 Coder 480B", contextWindow: 256000, capabilities: ["code", "reasoning"], description: "免费编程" },
      { id: "hf:Qwen/Qwen3-VL-235B-A22B-Instruct", name: "Qwen3 VL 235B", contextWindow: 250000, capabilities: ["chat", "vision"], description: "免费视觉" },
      { id: "hf:openai/gpt-oss-120b", name: "GPT OSS 120B", contextWindow: 128000, capabilities: ["chat", "code"], description: "OpenAI 开源" },
    ],
  },
  {
    id: "github-copilot",
    name: "GitHub Copilot",
    icon: "code",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "ghp_...",
    apiKeyHint: "使用 GitHub Token (需 Copilot 订阅)",
    models: [
      { id: "gpt-4o", name: "GPT-4o", contextWindow: 128000, capabilities: ["chat", "code", "vision"], recommended: true, description: "Copilot 默认" },
      { id: "gpt-4.1", name: "GPT-4.1", contextWindow: 128000, capabilities: ["chat", "code", "vision"], description: "百万上下文" },
      { id: "gpt-4.1-mini", name: "GPT-4.1 Mini", contextWindow: 128000, capabilities: ["chat", "code", "vision"], recommended: true, description: "高性价比" },
      { id: "o3-mini", name: "o3-mini", contextWindow: 128000, capabilities: ["chat", "code", "reasoning"], description: "推理模型" },
    ],
  },
  {
    id: "cloudflare",
    name: "Cloudflare AI Gateway",
    icon: "cloud_sync",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "your-api-key",
    apiKeyHint: "从 dash.cloudflare.com 获取",
    models: [
      { id: "claude-sonnet-4-5", name: "Claude Sonnet 4.5", contextWindow: 200000, capabilities: ["chat", "code", "reasoning", "vision"], recommended: true, description: "经 Cloudflare 代理" },
    ],
  },
  {
    id: "amazon-bedrock",
    name: "Amazon Bedrock",
    icon: "cloud_queue",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "AWS_PROFILE 或 Access Key",
    apiKeyHint: "配置 AWS 凭证 (aws configure)",
    models: [
      { id: "anthropic.claude-sonnet-4-5-v2", name: "Claude Sonnet 4.5", contextWindow: 200000, capabilities: ["chat", "code", "reasoning", "vision"], recommended: true, description: "Bedrock 托管" },
      { id: "anthropic.claude-haiku-3-5-v1", name: "Claude Haiku 3.5", contextWindow: 200000, capabilities: ["chat", "code", "vision"], description: "低成本" },
      { id: "amazon.nova-pro-v1", name: "Amazon Nova Pro", contextWindow: 300000, capabilities: ["chat", "code", "vision"], description: "Amazon 自研" },
    ],
  },

  // ─── 本地部署 ──────────────────────────────────
  {
    id: "ollama",
    name: "Ollama 本地部署",
    icon: "computer",
    description: "",
    apiKeyPrefix: "",
    apiKeyPlaceholder: "",
    apiKeyHint: "需先安装 Ollama: ollama.com/download",
    models: [
      { id: "qwen3:32b", name: "Qwen3 32B", contextWindow: 128000, capabilities: ["chat", "code", "reasoning"], recommended: true, description: "本地推理首选" },
      { id: "llama3.3:70b", name: "Llama 3.3 70B", contextWindow: 128000, capabilities: ["chat", "code"], description: "Meta 开源" },
      { id: "deepseek-r1:32b", name: "DeepSeek R1 32B", contextWindow: 128000, capabilities: ["chat", "reasoning"], description: "本地推理" },
      { id: "gemma3:27b", name: "Gemma 3 27B", contextWindow: 128000, capabilities: ["chat", "vision"], description: "Google 多模态" },
    ],
  },
];

// ─── Onboarding Store ───

export type OnboardingStep = 1 | 2 | 3;

interface OnboardingState {
  needsSetup: boolean;
  setNeedsSetup: (v: boolean) => void;

  step: OnboardingStep;
  selectedProvider: string | null;
  selectProvider: (id: string) => void;

  apiKey: string;
  setApiKey: (key: string) => void;
  apiKeyError: string | null;
  setApiKeyError: (err: string | null) => void;
  validatingKey: boolean;
  setValidatingKey: (v: boolean) => void;

  selectedModels: string[];
  toggleModel: (id: string) => void;

  nextStep: () => void;
  prevStep: () => void;

  saving: boolean;
  setSaving: (v: boolean) => void;

  reset: () => void;
}

export const useOnboardingStore = create<OnboardingState>((set, get) => ({
  needsSetup: false,
  setNeedsSetup: (v) => set({ needsSetup: v }),

  step: 1,
  selectedProvider: null,
  selectProvider: (id) => {
    set({ selectedProvider: id, apiKey: "", apiKeyError: null, selectedModels: [] });
  },

  apiKey: "",
  setApiKey: (key) => set({ apiKey: key, apiKeyError: null }),
  apiKeyError: null,
  setApiKeyError: (err) => set({ apiKeyError: err }),
  validatingKey: false,
  setValidatingKey: (v) => set({ validatingKey: v }),

  selectedModels: [],
  toggleModel: (id) => {
    const current = get().selectedModels;
    if (current.includes(id)) {
      set({ selectedModels: current.filter((m) => m !== id) });
    } else {
      set({ selectedModels: [...current, id] });
    }
  },

  nextStep: () => {
    const s = get().step;
    if (s < 3) set({ step: (s + 1) as OnboardingStep });
  },
  prevStep: () => {
    const s = get().step;
    if (s > 1) set({ step: (s - 1) as OnboardingStep });
  },

  saving: false,
  setSaving: (v) => set({ saving: v }),

  reset: () =>
    set({
      step: 1,
      selectedProvider: null,
      apiKey: "",
      apiKeyError: null,
      validatingKey: false,
      selectedModels: [],
      saving: false,
    }),
}));
