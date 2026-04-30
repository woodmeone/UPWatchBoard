#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 分析模块 - 支持 OpenAI 兼容 API

支持的模型:
- OpenAI (GPT-4, GPT-3.5)
- Claude (via OpenAI 兼容接口)
- 本地模型 (Ollama, vLLM, LM Studio 等)
- 国内模型 (DeepSeek, 通义千问, 智谱 等)

数据指标体系:
- 流量指标: 播放量、游客占比、粉丝观看率
- 内容指标: 封标点击率、3秒跳出率、平均播放进度
- 互动指标: 互动率、点赞/评论/弹幕/收藏/投币/转发
- 转化指标: 涨粉量、播转粉率
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "data" / "ai_config.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "provider": "openai",
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "max_tokens": 4000,
    "temperature": 0.7,
}

PROVIDER_PRESETS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"]
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"]
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4", "glm-4-flash", "glm-3-turbo"]
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "models": ["llama3", "qwen2", "deepseek-v2"]
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "models": ["local-model"]
    },
    "custom": {
        "base_url": "",
        "models": []
    }
}


@dataclass
class MetricAnomaly:
    """异常指标数据结构"""
    metric_name: str
    metric_value: float
    threshold: float
    severity: str  # "high", "medium", "low"
    description: str


@dataclass
class VideoMetrics:
    """单视频指标数据结构"""
    title: str
    plays: int
    visitor_play_pct: float
    fan_view_rate: float
    ctr_star: float
    bounce_3s: float
    interact_rate: float
    gain_fans: int
    likes: int
    comments: int
    danmaku: int
    favorites: int
    coins: int
    shares: int
    avg_progress: float
    
    @property
    def play_gain_fans_rate(self) -> float:
        if self.plays == 0:
            return 0.0
        return self.gain_fans / self.plays * 100
    
    @property
    def like_rate(self) -> float:
        if self.plays == 0:
            return 0.0
        return self.likes / self.plays * 100
    
    @property
    def comment_rate(self) -> float:
        if self.plays == 0:
            return 0.0
        return self.comments / self.plays * 100
    
    @property
    def favorite_rate(self) -> float:
        if self.plays == 0:
            return 0.0
        return self.favorites / self.plays * 100
    
    @property
    def coin_rate(self) -> float:
        if self.plays == 0:
            return 0.0
        return self.coins / self.plays * 100
    
    @property
    def share_rate(self) -> float:
        if self.plays == 0:
            return 0.0
        return self.shares / self.plays * 100
    
    @property
    def retention_3s(self) -> float:
        return 100 - self.bounce_3s


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] 保存 AI 配置失败: {e}")
        return False


def call_ai_api(prompt: str, config: dict = None) -> dict:
    if config is None:
        config = load_config()

    if not config.get("api_key") and not config.get("provider") == "ollama":
        return {
            "ok": False,
            "error": "未配置 API Key，请先在设置中配置",
            "content": ""
        }

    base_url = config.get("base_url", DEFAULT_CONFIG["base_url"]).rstrip("/")
    api_key = config.get("api_key", "")
    model = config.get("model", DEFAULT_CONFIG["model"])
    max_tokens = config.get("max_tokens", DEFAULT_CONFIG["max_tokens"])
    temperature = config.get("temperature", DEFAULT_CONFIG["temperature"])

    url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                return {
                    "ok": True,
                    "error": "",
                    "content": content,
                    "model": model,
                    "usage": result.get("usage", {})
                }
            else:
                return {
                    "ok": False,
                    "error": f"API 返回格式异常: {result}",
                    "content": ""
                }

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        return {
            "ok": False,
            "error": f"HTTP {e.code}: {error_body}",
            "content": ""
        }
    except urllib.error.URLError as e:
        return {
            "ok": False,
            "error": f"网络错误: {e.reason}",
            "content": ""
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"调用失败: {str(e)}",
            "content": ""
        }


def get_system_prompt() -> str:
    return """你是一位资深的B站数据分析专家，拥有丰富的UP主运营经验和数据洞察能力。你的任务是深入分析UP主的视频数据，提供专业、可执行的优化建议。

## 你的专业能力

1. **数据解读能力**：能够准确理解B站各项数据指标的含义及其相互关系
2. **模式识别能力**：从数据中发现趋势、异常和潜在问题
3. **策略制定能力**：基于数据分析给出具体、可执行的优化方案
4. **行业洞察力**：了解B站算法推荐机制和用户行为特征

## 数据指标体系说明

### 一、流量指标
| 指标 | 含义 | 优秀基准 | 警戒线 |
|------|------|----------|--------|
| 播放量 | 视频被观看的总次数 | >5000 | <1000 |
| 游客播放占比 | 非粉丝观看占比，反映内容破圈能力 | 70-90% | >95%或<50% |
| 粉丝观看率 | 粉丝观看人数/粉丝总数 | >5% | <2% |

### 二、内容指标
| 指标 | 含义 | 优秀基准 | 警戒线 |
|------|------|----------|--------|
| 封标点击率 | 封面标题吸引力评分(1-5星) | ≥4星 | <3星 |
| 3秒跳出率 | 观众在3秒内离开的比例 | <25% | >40% |
| 平均播放进度 | 观众平均观看时长占比 | >40% | <25% |

### 三、互动指标
| 指标 | 含义 | 优秀基准 | 警戒线 |
|------|------|----------|--------|
| 互动率 | (点赞+评论+弹幕+收藏+投币+转发)/播放量 | >8% | <3% |
| 点赞率 | 点赞/播放量 | >5% | <2% |
| 评论率 | 评论/播放量 | >0.5% | <0.1% |
| 收藏率 | 收藏/播放量 | >2% | <0.5% |
| 投币率 | 投币/播放量 | >1% | <0.3% |

### 四、转化指标
| 指标 | 含义 | 优秀基准 | 警戒线 |
|------|------|----------|--------|
| 涨粉量 | 视频带来的新增粉丝数 | >50 | <10 |
| 播转粉率 | 涨粉量/播放量 | >1% | <0.3% |

## 分析框架

请按照以下结构进行分析：

### 1. 数据总览与评分解读
- 四维度健康度评分解读
- 整体表现概述

### 2. 异常数据识别
- 识别异常指标（超出警戒线）
- 分析异常原因

### 3. 单视频深度分析
- 表现最佳视频的成功因素
- 表现欠佳视频的问题诊断

### 4. 多视频对比分析
- 视频间表现差异
- 成功模式的共性提取

### 5. 趋势分析（如有历史数据）
- 数据变化趋势
- 需要关注的信号

### 6. 优化建议
- 按优先级排序的具体建议
- 每条建议需包含：问题、原因、解决方案、预期效果

### 7. 下期视频建议
- 选题方向建议
- 制作要点提醒

## 输出要求

1. 使用 Markdown 格式，结构清晰
2. 引用具体数据支撑观点
3. 建议要具体可执行，避免泛泛而谈
4. 使用专业术语但确保易于理解
5. 突出重点，使用加粗标记关键信息
6. 每个分析点都要有数据依据

请用中文回复。"""


def detect_anomalies(videos: List[Dict], scores: Dict) -> List[MetricAnomaly]:
    """检测异常数据指标"""
    anomalies = []
    
    for v in videos:
        title = v.get("title", "未知视频")
        
        if v.get("bounce_3s", 0) > 40:
            anomalies.append(MetricAnomaly(
                metric_name=f"「{title}」3秒跳出率",
                metric_value=v.get("bounce_3s", 0),
                threshold=40,
                severity="high",
                description=f"跳出率{v.get('bounce_3s', 0):.1f}%超过警戒线40%，视频开头吸引力严重不足"
            ))
        elif v.get("bounce_3s", 0) > 30:
            anomalies.append(MetricAnomaly(
                metric_name=f"「{title}」3秒跳出率",
                metric_value=v.get("bounce_3s", 0),
                threshold=30,
                severity="medium",
                description=f"跳出率{v.get('bounce_3s', 0):.1f}%偏高，需优化视频开头"
            ))
        
        if v.get("ctr_star", 0) < 3:
            anomalies.append(MetricAnomaly(
                metric_name=f"「{title}」封标点击率",
                metric_value=v.get("ctr_star", 0),
                threshold=3,
                severity="high",
                description=f"点击率仅{v.get('ctr_star', 0):.1f}星，封面标题吸引力严重不足"
            ))
        
        if v.get("avg_progress", 0) < 25:
            anomalies.append(MetricAnomaly(
                metric_name=f"「{title}」平均播放进度",
                metric_value=v.get("avg_progress", 0),
                threshold=25,
                severity="high",
                description=f"播放进度仅{v.get('avg_progress', 0):.1f}%，内容留存能力差"
            ))
        
        if v.get("interact_rate", 0) < 3:
            anomalies.append(MetricAnomaly(
                metric_name=f"「{title}」互动率",
                metric_value=v.get("interact_rate", 0),
                threshold=3,
                severity="medium",
                description=f"互动率仅{v.get('interact_rate', 0):.1f}%，缺乏互动引导"
            ))
        
        if v.get("plays", 0) > 0:
            gain_rate = v.get("gain_fans", 0) / v.get("plays", 0) * 100
            if gain_rate < 0.3:
                anomalies.append(MetricAnomaly(
                    metric_name=f"「{title}」播转粉率",
                    metric_value=gain_rate,
                    threshold=0.3,
                    severity="medium",
                    description=f"播转粉率仅{gain_rate:.2f}%，涨粉转化能力弱"
                ))
        
        if v.get("visitor_play_pct", 0) > 95:
            anomalies.append(MetricAnomaly(
                metric_name=f"「{title}」游客播放占比",
                metric_value=v.get("visitor_play_pct", 0),
                threshold=95,
                severity="low",
                description=f"游客占比{v.get('visitor_play_pct', 0):.1f}%过高，粉丝基数小或内容过于泛化"
            ))
    
    if scores:
        for dim, name in [
            ("traffic_acquisition", "流量获取能力"),
            ("content_appeal", "内容吸引力"),
            ("content_quality", "内容质量"),
            ("fan_conversion", "粉丝转化能力")
        ]:
            score = scores.get(dim, 0)
            if score < 40:
                anomalies.append(MetricAnomaly(
                    metric_name=f"维度评分：{name}",
                    metric_value=score,
                    threshold=40,
                    severity="high",
                    description=f"{name}评分仅{score:.0f}分，需要重点优化"
                ))
            elif score < 60:
                anomalies.append(MetricAnomaly(
                    metric_name=f"维度评分：{name}",
                    metric_value=score,
                    threshold=60,
                    severity="medium",
                    description=f"{name}评分{score:.0f}分，有提升空间"
                ))
    
    return anomalies


def format_video_data_for_prompt(videos: List[Dict]) -> str:
    """格式化视频数据用于AI分析"""
    lines = []
    lines.append("| 视频标题 | 播放量 | 游客占比 | 粉丝观看率 | 点击率 | 3秒跳出 | 播放进度 | 互动率 | 涨粉 | 点赞 | 评论 | 弹幕 | 收藏 | 投币 | 转发 |")
    lines.append("|----------|--------|----------|------------|--------|---------|----------|--------|------|------|------|------|------|------|------|")
    
    for v in videos:
        title = v.get("title", "未知")[:15]
        plays = v.get("plays", 0)
        visitor = v.get("visitor_play_pct", 0)
        fan_rate = v.get("fan_view_rate", 0)
        ctr = v.get("ctr_star", 0)
        bounce = v.get("bounce_3s", 0)
        progress = v.get("avg_progress", 0)
        interact = v.get("interact_rate", 0)
        gain = v.get("gain_fans", 0)
        likes = v.get("likes", 0)
        comments = v.get("comments", 0)
        danmaku = v.get("danmaku", 0)
        favorites = v.get("favorites", 0)
        coins = v.get("coins", 0)
        shares = v.get("shares", 0)
        
        lines.append(f"| {title} | {plays} | {visitor:.1f}% | {fan_rate:.1f}% | {ctr:.1f}星 | {bounce:.1f}% | {progress:.1f}% | {interact:.1f}% | {gain} | {likes} | {comments} | {danmaku} | {favorites} | {coins} | {shares} |")
    
    return "\n".join(lines)


def format_history_data_for_prompt(history: List[Dict]) -> str:
    """格式化历史数据用于AI分析"""
    if not history:
        return "暂无历史数据"
    
    lines = []
    lines.append("| 日期 | 播放量 | 累计粉丝 | 点赞 | 收藏 | 硬币 | 评论 | 弹幕 | 分享 |")
    lines.append("|------|--------|----------|------|------|------|------|------|------|")
    
    for h in history[-10:]:
        date = h.get("date", "")[-8:] if h.get("date") else ""
        plays = h.get("plays", 0)
        fans = h.get("fans", 0)
        likes = h.get("likes", 0)
        favorites = h.get("favorites", 0)
        coins = h.get("coins", 0)
        comments = h.get("comments", 0)
        danmaku = h.get("danmaku", 0)
        shares = h.get("shares", 0)
        
        lines.append(f"| {date} | {plays} | {fans} | {likes} | {favorites} | {coins} | {comments} | {danmaku} | {shares} |")
    
    return "\n".join(lines)


def format_anomalies_for_prompt(anomalies: List[MetricAnomaly]) -> str:
    """格式化异常数据用于AI分析"""
    if not anomalies:
        return "未检测到明显异常指标"
    
    high_severity = [a for a in anomalies if a.severity == "high"]
    medium_severity = [a for a in anomalies if a.severity == "medium"]
    low_severity = [a for a in anomalies if a.severity == "low"]
    
    lines = []
    
    if high_severity:
        lines.append("### 🔴 高优先级异常（需立即处理）")
        for a in high_severity:
            lines.append(f"- **{a.metric_name}**: {a.description}")
    
    if medium_severity:
        lines.append("\n### 🟡 中优先级异常（建议优化）")
        for a in medium_severity:
            lines.append(f"- **{a.metric_name}**: {a.description}")
    
    if low_severity:
        lines.append("\n### 🟢 低优先级异常（可关注）")
        for a in low_severity:
            lines.append(f"- **{a.metric_name}**: {a.description}")
    
    return "\n".join(lines)


def build_analysis_prompt(analysis_data: dict) -> str:
    """构建完整的AI分析提示词"""
    
    scores = analysis_data.get("scores", {})
    patterns = analysis_data.get("patterns", [])
    highlights = analysis_data.get("highlights", [])
    issues = analysis_data.get("issues", [])
    suggestions = analysis_data.get("suggestions", [])
    next_video_advice = analysis_data.get("next_video_advice", [])
    
    videos = analysis_data.get("videos", [])
    history = analysis_data.get("history", [])
    
    anomalies = detect_anomalies(videos, scores)
    
    total_plays = sum(v.get("plays", 0) for v in videos)
    total_gain = sum(v.get("gain_fans", 0) for v in videos)
    avg_bounce = sum(v.get("bounce_3s", 0) for v in videos) / len(videos) if videos else 0
    avg_progress = sum(v.get("avg_progress", 0) for v in videos) / len(videos) if videos else 0
    avg_interact = sum(v.get("interact_rate", 0) for v in videos) / len(videos) if videos else 0
    avg_visitor = sum(v.get("visitor_play_pct", 0) for v in videos) / len(videos) if videos else 0
    
    prompt = f"""请深入分析以下B站UP主的视频数据，提供专业的数据洞察和优化建议。

## 一、四维度健康度评分

| 维度 | 分数 | 评价 |
|------|------|------|
| 流量获取能力 | {scores.get('traffic_acquisition', 0)} 分 | {get_score_level(scores.get('traffic_acquisition', 0))} |
| 内容吸引力 | {scores.get('content_appeal', 0)} 分 | {get_score_level(scores.get('content_appeal', 0))} |
| 内容质量 | {scores.get('content_quality', 0)} 分 | {get_score_level(scores.get('content_quality', 0))} |
| 粉丝转化能力 | {scores.get('fan_conversion', 0)} 分 | {get_score_level(scores.get('fan_conversion', 0))} |
| **综合评分** | **{scores.get('overall', 0)} 分** | **{get_score_level(scores.get('overall', 0))}** |

## 二、整体数据概览

- **分析视频数量**: {len(videos)} 条
- **总播放量**: {format_num(total_plays)}
- **净涨粉**: +{format_num(total_gain)}
- **平均3秒跳出率**: {avg_bounce:.1f}%
- **平均播放进度**: {avg_progress:.1f}%
- **平均互动率**: {avg_interact:.1f}%
- **平均游客占比**: {avg_visitor:.1f}%

## 三、异常数据识别

{format_anomalies_for_prompt(anomalies)}

## 四、详细视频数据

{format_video_data_for_prompt(videos)}

## 五、历史数据趋势（最近10天）

{format_history_data_for_prompt(history)}

## 六、系统识别的数据模式

{chr(10).join(f'- {p}' for p in patterns) if patterns else '- 暂无明显数据模式'}

## 七、亮点分析

{chr(10).join(f'- {h}' for h in highlights) if highlights else '- 暂无明显亮点'}

## 八、问题诊断

{chr(10).join(f'- {i}' for i in issues) if issues else '- 暂无明显问题'}

## 九、基础优化建议

{chr(10).join(f'{idx+1}. {s}' for idx, s in enumerate(suggestions)) if suggestions else '- 暂无建议'}

---

请基于以上完整数据，进行深入分析并给出专业的优化建议。重点关注：

1. **评分解读**：详细解读四维度评分的含义和改进方向
2. **异常分析**：深入分析异常指标的原因和解决方案
3. **视频对比**：对比分析不同视频的表现差异，提取成功模式
4. **趋势洞察**：如有历史数据，分析趋势变化
5. **优化建议**：给出具体、可执行的优化方案，按优先级排序
6. **下期建议**：为下期视频提供选题和制作建议

请确保每个分析点都有数据支撑，建议要具体可执行。"""

    return prompt


def get_score_level(score: int) -> str:
    if score >= 80:
        return "优秀 🟢"
    elif score >= 60:
        return "良好 🟡"
    elif score >= 40:
        return "一般 🟠"
    else:
        return "需改进 🔴"


def format_num(n: int) -> str:
    if n >= 10000:
        return f"{n/10000:.1f}万"
    return str(n)


def get_providers() -> dict:
    return PROVIDER_PRESETS
