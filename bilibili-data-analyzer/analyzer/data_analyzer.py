#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站数据分析引擎

基于 metrics-guide.md 指标体系，自动解析CSV数据并生成：
  - 四维度健康度评分（流量获取/内容吸引力/内容质量/粉丝转化）
  - 8种常见数据模式识别
  - 结构化优化建议

用法：
  analyzer = DataAnalyzer()
  result = analyzer.analyze("data/近期稿件对比.csv", "data/历史累计数据趋势.csv")
  print(result.to_markdown())
"""

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


def _pct(s) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    return float(str(s).replace("%", "").strip()) or 0


def _num(s) -> int:
    if isinstance(s, (int, float)):
        return int(s)
    return int(str(s).replace(",", "").replace("万", "0000").strip()) or 0


def _star(s) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    return float(str(s).replace("星", "").strip()) or 0


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class VideoRecord:
    title: str
    publish_time: str
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
    def fan_view_rate_pct(self) -> float:
        return self.fan_view_rate

    @property
    def play_gain_fans_rate(self) -> float:
        if self.plays == 0:
            return 0.0
        return self.gain_fans / self.plays * 100


@dataclass
class HistoryRecord:
    date: str
    plays: int
    fans: int
    likes: int
    favorites: int
    coins: int
    comments: int
    danmaku: int
    shares: int


@dataclass
class HealthScores:
    traffic_acquisition: float
    content_appeal: float
    content_quality: float
    fan_conversion: float

    @property
    def overall(self) -> float:
        return (self.traffic_acquisition + self.content_appeal
                + self.content_quality + self.fan_conversion) / 4


@dataclass
class AnalysisResult:
    videos: list = field(default_factory=list)
    history: list = field(default_factory=list)
    scores: Optional[HealthScores] = None
    patterns: list = field(default_factory=list)
    highlights: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    next_video_advice: list = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = []
        lines.append("## 📊 数据总览")
        if self.scores:
            grade = _score_grade(self.scores.overall)
            lines.append(f"综合健康度评分：**{self.scores.overall:.0f}分**（{grade}）")
            lines.append(f"- 流量获取能力：{self.scores.traffic_acquisition:.0f}分")
            lines.append(f"- 内容吸引力：{self.scores.content_appeal:.0f}分")
            lines.append(f"- 内容质量：{self.scores.content_quality:.0f}分")
            lines.append(f"- 粉丝转化能力：{self.scores.fan_conversion:.0f}分")

        total_plays = sum(v.plays for v in self.videos)
        total_gain = sum(v.gain_fans for v in self.videos)
        lines.append(f"分析 {len(self.videos)} 条视频，总播放 {_format_num(total_plays)}，净涨粉 +{_format_num(total_gain)}")

        if self.highlights:
            lines.append("")
            lines.append("## ✅ 亮点分析")
            for h in self.highlights:
                lines.append(f"- {h}")

        if self.issues:
            lines.append("")
            lines.append("## ⚠️ 问题诊断")
            for i in self.issues:
                lines.append(f"- {i}")

        if self.patterns:
            lines.append("")
            lines.append("## 🔍 数据模式识别")
            for p in self.patterns:
                lines.append(f"- {p}")

        if self.suggestions:
            lines.append("")
            lines.append("## 🎯 优化建议（按优先级）")
            for idx, s in enumerate(self.suggestions, 1):
                lines.append(f"{idx}. {s}")

        if self.next_video_advice:
            lines.append("")
            lines.append("## 📌 下期视频建议")
            for a in self.next_video_advice:
                lines.append(f"- {a}")

        return "\n".join(lines)

    def to_json(self) -> dict:
        videos_data = []
        for v in self.videos:
            videos_data.append({
                "title": v.title,
                "publish_time": v.publish_time,
                "plays": v.plays,
                "visitor_play_pct": v.visitor_play_pct,
                "fan_view_rate": v.fan_view_rate,
                "ctr_star": v.ctr_star,
                "bounce_3s": v.bounce_3s,
                "interact_rate": v.interact_rate,
                "gain_fans": v.gain_fans,
                "likes": v.likes,
                "comments": v.comments,
                "danmaku": v.danmaku,
                "favorites": v.favorites,
                "coins": v.coins,
                "shares": v.shares,
                "avg_progress": v.avg_progress,
                "play_gain_fans_rate": v.play_gain_fans_rate,
            })
        
        history_data = []
        for h in self.history:
            history_data.append({
                "date": h.date,
                "plays": h.plays,
                "fans": h.fans,
                "likes": h.likes,
                "favorites": h.favorites,
                "coins": h.coins,
                "comments": h.comments,
                "danmaku": h.danmaku,
                "shares": h.shares,
            })
        
        return {
            "scores": {
                "traffic_acquisition": self.scores.traffic_acquisition if self.scores else 0,
                "content_appeal": self.scores.content_appeal if self.scores else 0,
                "content_quality": self.scores.content_quality if self.scores else 0,
                "fan_conversion": self.scores.fan_conversion if self.scores else 0,
                "overall": self.scores.overall if self.scores else 0,
            },
            "patterns": self.patterns,
            "highlights": self.highlights,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "next_video_advice": self.next_video_advice,
            "videos": videos_data,
            "history": history_data,
            "markdown": self.to_markdown(),
        }


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _format_num(n: int) -> str:
    if n >= 10000:
        return f"{n/10000:.1f}万"
    return str(n)


def _score_grade(score: float) -> str:
    if score >= 80:
        return "优秀 🟢"
    elif score >= 60:
        return "良好 🟡"
    elif score >= 40:
        return "一般 🟠"
    return "需改进 🔴"


# ---------------------------------------------------------------------------
# CSV 解析
# ---------------------------------------------------------------------------

def parse_video_csv(csv_path: str) -> list:
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            try:
                rows.append(VideoRecord(
                    title=r.get("视频标题", "").strip(),
                    publish_time=r.get("发布时间", "").strip(),
                    plays=_num(r.get("播放量", 0)),
                    visitor_play_pct=_pct(r.get("游客播放占比", 0)),
                    fan_view_rate=_pct(r.get("粉丝观看率", 0)),
                    ctr_star=_star(r.get("封标点击率", 0)),
                    bounce_3s=_pct(r.get("3秒跳出率", 0)),
                    interact_rate=_pct(r.get("互动率", 0)),
                    gain_fans=_num(r.get("涨粉量", 0)),
                    likes=_num(r.get("点赞量", 0)),
                    comments=_num(r.get("评论量", 0)),
                    danmaku=_num(r.get("弹幕量", 0)),
                    favorites=_num(r.get("收藏量", 0)),
                    coins=_num(r.get("投币量", 0)),
                    shares=_num(r.get("转发量", 0)),
                    avg_progress=_pct(r.get("平均播放进度", 0)),
                ))
            except Exception:
                continue
        return rows


def parse_history_csv(csv_path: str) -> list:
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            try:
                rows.append(HistoryRecord(
                    date=r.get("时间", "").strip(),
                    plays=_num(r.get("播放量", 0)),
                    fans=_num(r.get("累计粉丝", 0)),
                    likes=_num(r.get("点赞", 0)),
                    favorites=_num(r.get("收藏", 0)),
                    coins=_num(r.get("硬币", 0)),
                    comments=_num(r.get("评论", 0)),
                    danmaku=_num(r.get("弹幕", 0)),
                    shares=_num(r.get("分享", 0)),
                ))
            except Exception:
                continue
        return rows


# ---------------------------------------------------------------------------
# 核心分析引擎
# ---------------------------------------------------------------------------

class DataAnalyzer:
    """
    B站数据分析器：评估健康度、识别模式、生成建议。
    """

    def __init__(self):
        pass

    def analyze(self, video_csv_path: str, history_csv_path: str = "") -> AnalysisResult:
        videos = parse_video_csv(video_csv_path)
        history = parse_history_csv(history_csv_path) if history_csv_path else []

        if not videos:
            result = AnalysisResult()
            result.patterns = ["暂无视频数据可用于分析"]
            return result

        result = AnalysisResult(videos=videos, history=history)
        result.scores = self._calc_health_scores(videos)
        result.patterns = self._detect_patterns(videos, history)
        result.highlights = self._find_highlights(videos)
        result.issues = self._find_issues(videos)
        result.suggestions = self._generate_suggestions(videos, result.scores, result.patterns, result.issues)
        result.next_video_advice = self._generate_next_video_advice(videos, result.scores, result.patterns)
        return result

    # ---- 四维度评分 ----

    def _calc_health_scores(self, videos: list) -> HealthScores:
        n = len(videos)

        # === 维度1：流量获取能力 (25%) ===
        avg_plays = sum(v.plays for v in videos) / n
        plays_trend = _calc_trend([v.plays for v in videos])
        visitor_scores = []
        for v in videos:
            vp = v.visitor_play_pct
            if 70 <= vp <= 90:
                visitor_scores.append(100)
            elif 50 <= vp < 70:
                visitor_scores.append(70)
            elif 90 < vp <= 95:
                visitor_scores.append(70)
            elif vp < 50:
                visitor_scores.append(40)
            else:
                visitor_scores.append(60)
        avg_visitor = sum(visitor_scores) / n

        traffic = 0
        if plays_trend > 0:
            traffic += 50
        elif plays_trend == 0:
            traffic += 30
        else:
            traffic += 10
        traffic += avg_visitor * 0.5
        traffic = min(100, traffic)

        # === 维度2：内容吸引力 (25%) ===
        ctr_scores = []
        for v in videos:
            if v.ctr_star >= 4:
                ctr_scores.append(100)
            elif v.ctr_star >= 3:
                ctr_scores.append(60)
            else:
                ctr_scores.append(30)
        avg_ctr = sum(ctr_scores) / n

        bounce_scores = []
        for v in videos:
            if v.bounce_3s < 30:
                bounce_scores.append(100)
            elif v.bounce_3s <= 40:
                bounce_scores.append(60)
            else:
                bounce_scores.append(30)
        avg_bounce = sum(bounce_scores) / n

        content_appeal = (avg_ctr * 0.6 + avg_bounce * 0.4)
        content_appeal = min(100, content_appeal)

        # === 维度3：内容质量 (25%) ===
        progress_scores = []
        for v in videos:
            if v.avg_progress > 40:
                progress_scores.append(100)
            elif v.avg_progress >= 25:
                progress_scores.append(60)
            else:
                progress_scores.append(30)
        avg_progress = sum(progress_scores) / n

        interact_scores = []
        for v in videos:
            if v.interact_rate > 8:
                interact_scores.append(100)
            elif v.interact_rate >= 4:
                interact_scores.append(70)
            elif v.interact_rate >= 2:
                interact_scores.append(40)
            else:
                interact_scores.append(20)
        avg_interact = sum(interact_scores) / n

        content_quality = (avg_progress * 0.5 + avg_interact * 0.5)
        content_quality = min(100, content_quality)

        # === 维度4：粉丝转化能力 (25%) ===
        gain_scores = []
        for v in videos:
            rate = v.play_gain_fans_rate
            if rate > 2:
                gain_scores.append(100)
            elif rate >= 1:
                gain_scores.append(70)
            elif rate >= 0.5:
                gain_scores.append(40)
            else:
                gain_scores.append(20)
        avg_gain = sum(gain_scores) / n

        fan_conversion = avg_gain
        fan_conversion = min(100, fan_conversion)

        return HealthScores(
            traffic_acquisition=round(traffic),
            content_appeal=round(content_appeal),
            content_quality=round(content_quality),
            fan_conversion=round(fan_conversion),
        )

    # ---- 模式识别 ----

    def _detect_patterns(self, videos: list, history: list) -> list:
        patterns = []
        n = len(videos)

        for v in videos:
            # 播放量高但跳出率也高
            if v.plays > 5000 and v.bounce_3s > 40:
                patterns.append(f"「{v.title}」播放量高但跳出率也高（{v.bounce_3s:.0f}%），封面标题与内容可能不符，观众预期落空")
            # 播放量低但播放进度高
            if v.plays < 5000 and v.avg_progress > 40:
                patterns.append(f"「{v.title}」播放量低但播放进度高（{v.avg_progress:.0f}%），内容质量好但曝光不足")
            # 互动率高但涨粉少
            if v.interact_rate > 6 and v.play_gain_fans_rate < 0.5:
                patterns.append(f"「{v.title}」互动率高但涨粉少，内容有吸引力但缺乏独特价值认同")
            # 游客占比极高
            if v.visitor_play_pct > 95:
                patterns.append(f"「{v.title}」游客占比极高（{v.visitor_play_pct:.0f}%），粉丝基数小或内容泛化")

        # 整体趋势模式
        if n >= 3:
            plays_list = [v.plays for v in videos]
            # 播放量逐期下降
            if all(plays_list[i] >= plays_list[i + 1] for i in range(len(plays_list) - 1)):
                patterns.append("播放量呈逐期下降趋势，建议复盘选题方向，尝试新形式")
            # 粉丝观看率持续走低
            fan_rates = [v.fan_view_rate for v in videos]
            if all(fan_rates[i] >= fan_rates[i + 1] for i in range(len(fan_rates) - 1)):
                patterns.append("粉丝观看率持续下降，内容可能偏离粉丝期待，建议关注粉丝画像变化")

        # 弹幕多但评论少
        for v in videos:
            if v.danmaku > v.comments * 2 and v.danmaku > 10:
                patterns.append(f"「{v.title}」弹幕({v.danmaku})远多于评论({v.comments})，观众沉浸观看但缺乏深度讨论意愿")
                break

        # 收藏率高但点赞率低
        for v in videos:
            if v.plays > 0:
                fav_rate = v.favorites / v.plays * 100
                like_rate = v.likes / v.plays * 100
                if fav_rate > 2 and like_rate < fav_rate:
                    patterns.append(f"「{v.title}」收藏率({fav_rate:.1f}%)高于点赞率({like_rate:.1f}%)，内容偏工具/干货型但情感共鸣不足")
                    break

        # 去重
        seen = set()
        unique = []
        for p in patterns:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return unique[:6]

    # ---- 亮点 ----

    def _find_highlights(self, videos: list) -> list:
        highlight = []

        best_plays = max(videos, key=lambda v: v.plays)
        highlight.append(f"播放量最高的视频「{best_plays.title}」达 {_format_num(best_plays.plays)} 次播放")

        best_ctr = max(videos, key=lambda v: v.ctr_star)
        if best_ctr.ctr_star >= 4:
            highlight.append(f"「{best_ctr.title}」封标点击率达 {best_ctr.ctr_star:.1f}星，封面标题表现优秀")

        best_interact = max(videos, key=lambda v: v.interact_rate)
        if best_interact.interact_rate > 5:
            highlight.append(f"「{best_interact.title}」互动率 {best_interact.interact_rate:.1f}%，观众参与度高")

        best_gain = max(videos, key=lambda v: v.gain_fans)
        if best_gain.gain_fans > 20:
            highlight.append(f"「{best_gain.title}」带来 {best_gain.gain_fans} 个新增粉丝，涨粉效果显著")

        best_progress = max(videos, key=lambda v: v.avg_progress)
        if best_progress.avg_progress > 40:
            highlight.append(f"「{best_progress.title}」平均播放进度 {best_progress.avg_progress:.0f}%，内容留存优秀")

        return highlight[:4]

    # ---- 问题 ----

    def _find_issues(self, videos: list) -> list:
        issues = []

        worst_bounce = max(videos, key=lambda v: v.bounce_3s)
        if worst_bounce.bounce_3s > 30:
            issues.append(f"「{worst_bounce.title}」3秒跳出率达 {worst_bounce.bounce_3s:.0f}%，视频开头吸引力不足")

        worst_ctr = min(videos, key=lambda v: v.ctr_star)
        if worst_ctr.ctr_star < 3.5:
            issues.append(f"「{worst_ctr.title}」封标点击率仅 {worst_ctr.ctr_star:.1f}星，封面和标题需优化")

        worst_progress = min(videos, key=lambda v: v.avg_progress)
        if worst_progress.avg_progress < 25:
            issues.append(f"「{worst_progress.title}」平均播放进度仅 {worst_progress.avg_progress:.0f}%，内容节奏需优化")

        worst_interact = min(videos, key=lambda v: v.interact_rate)
        if worst_interact.interact_rate < 3:
            issues.append(f"「{worst_interact.title}」互动率仅 {worst_interact.interact_rate:.1f}%，缺乏互动引导")

        n = len(videos)
        if n >= 2:
            avg_bounce = sum(v.bounce_3s for v in videos) / n
            if avg_bounce > 35:
                issues.append(f"整体平均跳出率 {avg_bounce:.0f}% 偏高，需系统性优化视频开头")

        return issues[:4]

    # ---- 建议生成 ----

    def _generate_suggestions(self, videos: list, scores: HealthScores, patterns: list, issues: list) -> list:
        suggestions = []

        if scores.traffic_acquisition < 50:
            suggestions.append("**封面与标题优化**（流量获取弱）：使用对比色封面、数字+悬念式标题，控制在20字以内；准备2-3个封面标题方案进行A/B测试；选择工作日18:00-22:00或周末全天发布")

        if scores.content_appeal < 50:
            suggestions.append("**开头优化**（点击率/跳出率不佳）：前3秒必须给出「为什么要看」的理由，避免冗长片头和自我介绍；用悬念、冲突或结论前置的方式抓住注意力")

        if scores.content_quality < 50:
            suggestions.append("**内容节奏优化**（留存不足）：控制视频时长在5-10分钟，每1-2分钟设置钩子点防止流失；去除冗余内容，保持信息密度；用画面切换和音效变化维持节奏感")

        if scores.fan_conversion < 50:
            suggestions.append("**互动引导优化**（涨粉转化弱）：在视频中自然引导一键三连和关注；设置开放性讨论话题引导评论；强化个人品牌辨识度，做系列化内容提升粉丝粘性")

        avg_bounce = sum(v.bounce_3s for v in videos) / len(videos) if videos else 0
        if avg_bounce > 35:
            suggestions.append("**针对性降低跳出率**：建议排查视频开头3秒画面是否吸引力不足、是否与封面承诺一致；可尝试将最精彩片段前置，制造期待感")

        avg_progress = sum(v.avg_progress for v in videos) / len(videos) if videos else 0
        if avg_progress < 30:
            suggestions.append("**提升播放完成度**：检查视频中段是否有信息密度下降、节奏拖沓的问题；建议用分段结构清晰标明进度，给观众完成预期")

        visitor_high = all(v.visitor_play_pct > 90 for v in videos)
        if visitor_high:
            suggestions.append("**发布策略优化**：游客占比过高，建议明确账号定位，深耕垂直领域；保持稳定更新频率（周更或双周更），培养粉丝观看习惯")

        return suggestions

    # ---- 下期建议 ----

    def _generate_next_video_advice(self, videos: list, scores: HealthScores, patterns: list) -> list:
        advice = []

        if not videos:
            return ["暂无足够数据生成建议，请先发布2-3期视频后再分析"]

        best = max(videos, key=lambda v: v.plays + v.interact_rate * 100 + v.gain_fans * 10)
        advice.append(f"参考表现最好的「{best.title}」的选题和风格，延续已验证的成功模式")

        if scores.content_appeal >= 60:
            advice.append("封面和开头的策略有效，继续保持；可在标题中尝试加入更多情绪词和数字增强点击欲")
        else:
            advice.append("下期重点优化封面标题和视频开头，制作2-3个版本进行内部比较后再最终选择")

        if scores.content_quality < 50:
            advice.append("增加干货密度：下期视频尝试将信息点排列更紧凑，减少铺垫和过渡，直接切入核心内容")
        else:
            advice.append("内容质量和互动表现不错，下期可尝试引导观众「关注看系列」，建立系列化内容预期")

        has_gain_issue = any("涨粉" in p for p in patterns)
        if has_gain_issue:
            advice.append("在视频结尾增加「关注获得更多」的明确引导和系列内容预告，将单次内容转化为持续追随的理由")

        return advice[:4]


# ---------------------------------------------------------------------------
# 趋势计算
# ---------------------------------------------------------------------------

def _calc_trend(values: list) -> int:
    if len(values) < 2:
        return 0
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0
    slope = num / den
    if slope > 0:
        return 1
    elif slope < 0:
        return -1
    return 0


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def analyze_data(video_csv_path: str, history_csv_path: str = "") -> AnalysisResult:
    analyzer = DataAnalyzer()
    return analyzer.analyze(video_csv_path, history_csv_path)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    video_path = sys.argv[1] if len(sys.argv) > 1 else "data/近期稿件对比.csv"
    history_path = sys.argv[2] if len(sys.argv) > 2 else "data/历史累计数据趋势.csv"

    result = analyze_data(video_path, history_path)
    print(result.to_markdown())

    json_path = "data/analysis_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result.to_json(), f, ensure_ascii=False, indent=2)
    print(f"\n分析结果已保存至: {json_path}")
