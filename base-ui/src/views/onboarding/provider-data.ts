export type ProviderInfo = {
  id: string;
  name: string;
  subtitle: string;
  tagline: string;
  icon: string; // Material Symbols icon name
  keyUrl: string;
  keyPlaceholder: string;
  recommended: boolean;
  priceRange: string;
  modelCount: number;
};

export const PROVIDERS: ProviderInfo[] = [
  {
    id: "anthropic",
    name: "Anthropic",
    subtitle: "Claude 系列",
    tagline: "最强推理与代码，深度思考能力卓越",
    icon: "psychology",
    keyUrl: "https://console.anthropic.com/settings/keys",
    keyPlaceholder: "sk-ant-api03-...",
    recommended: false,
    priceRange: "$0.8 ~ $25 / 1M tokens",
    modelCount: 3,
  },
  {
    id: "openai",
    name: "OpenAI",
    subtitle: "GPT 系列",
    tagline: "全能通用，生态最完善",
    icon: "auto_awesome",
    keyUrl: "https://platform.openai.com/api-keys",
    keyPlaceholder: "sk-...",
    recommended: false,
    priceRange: "$0.15 ~ $14 / 1M tokens",
    modelCount: 7,
  },
  {
    id: "google",
    name: "Google Gemini",
    subtitle: "Gemini 系列",
    tagline: "百万上下文，多模态领先",
    icon: "diamond",
    keyUrl: "https://aistudio.google.com/apikey",
    keyPlaceholder: "AIza...",
    recommended: false,
    priceRange: "$0.1 ~ $12 / 1M tokens",
    modelCount: 5,
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    subtitle: "V3.2 系列",
    tagline: "极致性价比，国产推理之光",
    icon: "explore",
    keyUrl: "https://platform.deepseek.com/api_keys",
    keyPlaceholder: "sk-...",
    recommended: false,
    priceRange: "$0.28 ~ $0.42 / 1M tokens",
    modelCount: 2,
  },
  {
    id: "nvidia",
    name: "NVIDIA NIM",
    subtitle: "20+ 顶级开源模型",
    tagline: "免费无限调用，Qwen / Kimi / MiniMax 全系列",
    icon: "developer_board",
    keyUrl: "https://build.nvidia.com/",
    keyPlaceholder: "nvapi-...",
    recommended: true,
    priceRange: "完全免费",
    modelCount: 18,
  },
  {
    id: "local",
    name: "本地模型",
    subtitle: "Ollama",
    tagline: "完全离线，数据不出本机",
    icon: "laptop_mac",
    keyUrl: "https://ollama.com/download",
    keyPlaceholder: "",
    recommended: false,
    priceRange: "免费",
    modelCount: 0, // user-defined
  },
];

export function getProvider(id: string): ProviderInfo | undefined {
  return PROVIDERS.find((p) => p.id === id);
}
