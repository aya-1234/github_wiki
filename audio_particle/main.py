"""
Audio-Reactive Free Particle Animation
音声入力で粒子の動きを直接変化させる・自由運動版

必要ライブラリ:
    pip install pygame numpy sounddevice
"""

import pygame
import numpy as np
import sounddevice as sd
import threading
import math
import random
import sys

# ════════════════════════════════════════════════════════════
#  設定
# ════════════════════════════════════════════════════════════
WIDTH, HEIGHT   = 1280, 800
FPS             = 60
NUM_PARTICLES   = 2000

SAMPLE_RATE     = 44100
BLOCK_SIZE      = 512          # 小さくして遅延を減らす

# 残像の長さ（大きいほど長く残る）
TRAIL_LEN       = 20

# ════════════════════════════════════════════════════════════
#  音声解析バッファ（スレッド間共有）
# ════════════════════════════════════════════════════════════
_audio = {
    "volume": 0.0,   # 全体音量    0〜1
    "bass":   0.0,   # 低音        0〜1
    "mid":    0.0,   # 中音        0〜1
    "high":   0.0,   # 高音        0〜1
    "beat":   False, # ビート検出
    "pitch":  0.0,   # 支配的周波数 (Hz)
}
_lock = threading.Lock()
_prev_bass = 0.0     # ビート検出用


def _audio_cb(indata, frames, time_info, status):
    global _prev_bass
    samples = indata[:, 0].astype(np.float32)

    # ── 音量 ──────────────────────────────────────────────
    rms    = float(np.sqrt(np.mean(samples ** 2)))
    volume = min(rms * 10.0, 1.0)

    # ── FFT ───────────────────────────────────────────────
    win = samples * np.hanning(len(samples))
    fft = np.abs(np.fft.rfft(win))
    freqs = np.fft.rfftfreq(len(samples), 1.0 / SAMPLE_RATE)

    def band(lo, hi):
        mask = (freqs >= lo) & (freqs < hi)
        return float(np.mean(fft[mask])) if mask.any() else 0.0

    raw_bass = band(20,   250)
    raw_mid  = band(250,  4000)
    raw_high = band(4000, 20000)
    total    = raw_bass + raw_mid + raw_high + 1e-9

    bass  = raw_bass / total
    mid   = raw_mid  / total
    high  = raw_high / total

    # ── 支配的ピッチ ──────────────────────────────────────
    peak_idx = int(np.argmax(fft[1:])) + 1
    pitch    = float(freqs[peak_idx]) if volume > 0.05 else 0.0

    # ── ビート検出（低音の急上昇）────────────────────────
    beat = (bass - _prev_bass) > 0.15 and volume > 0.1
    _prev_bass = bass * 0.7 + _prev_bass * 0.3

    # ── スムージングして書き込み ──────────────────────────
    s = 0.35   # 追従速度（大きいほど速く反応）
    with _lock:
        _audio["volume"] = _audio["volume"] * (1-s) + volume * s
        _audio["bass"]   = _audio["bass"]   * (1-s) + bass   * s
        _audio["mid"]    = _audio["mid"]    * (1-s) + mid    * s
        _audio["high"]   = _audio["high"]   * (1-s) + high   * s
        _audio["pitch"]  = pitch
        _audio["beat"]   = beat


def get_audio():
    with _lock:
        return dict(_audio)


# ════════════════════════════════════════════════════════════
#  パーティクル
# ════════════════════════════════════════════════════════════
class Particle:
    def __init__(self):
        self._spawn()

    def _spawn(self, burst_x=None, burst_y=None):
        """パーティクルを（再）生成"""
        if burst_x is not None:
            # ビート時：中心から爆発
            angle  = random.uniform(0, math.tau)
            speed  = random.uniform(2.0, 12.0)
            self.x = burst_x + math.cos(angle) * random.uniform(0, 30)
            self.y = burst_y + math.sin(angle) * random.uniform(0, 30)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
        else:
            # 通常：画面全体にランダム配置
            self.x  = random.uniform(0, WIDTH)
            self.y  = random.uniform(0, HEIGHT)
            angle   = random.uniform(0, math.tau)
            speed   = random.uniform(0.5, 3.0)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed

        self.life      = random.uniform(0.7, 1.0)
        self.max_life  = self.life
        self.base_size = random.uniform(1.5, 4.5)

        # 色：HSV → RGB（後で音声で色相をずらす）
        self.hue = random.uniform(0, 360)
        self.trail: list[tuple[float,float]] = []

    # ── 色計算 ──────────────────────────────────────────
    @staticmethod
    def hsv_to_rgb(h, s, v):
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        sector = int(h / 60)
        rgb_map = [
            (c, x, 0), (x, c, 0), (0, c, x),
            (0, x, c), (x, 0, c), (c, 0, x),
        ]
        r, g, b = rgb_map[sector % 6]
        return (int((r+m)*255), int((g+m)*255), int((b+m)*255))

    # ── 更新 ──────────────────────────────────────────────
    def update(self, t: float, av: dict, wind_x: float, wind_y: float):
        vol  = av["volume"]
        bass = av["bass"]
        mid  = av["mid"]
        high = av["high"]

        # ── 1. 自由飛行（慣性ベース）─────────────────────
        # 音量が大きいほど加速
        speed_boost = 1.0 + vol * 5.0

        # ── 2. 全体的な「風」（ゆったり変化するベクトル場）─
        wx = math.sin(self.x * 0.004 + t * 0.6) * math.cos(self.y * 0.003 - t * 0.4)
        wy = math.cos(self.x * 0.003 - t * 0.5) * math.sin(self.y * 0.004 + t * 0.7)

        # 低音 → 渦巻きを強化
        curl_strength = bass * 3.0
        cx = -wy * curl_strength
        cy =  wx * curl_strength

        # 中音 → 乱流（ランダムな小刻み振動）
        turb_scale = mid * 1.5
        tx = math.sin(self.x * 0.02 + t * 3.0 + self.hue) * turb_scale
        ty = math.cos(self.y * 0.02 - t * 2.5 + self.hue) * turb_scale

        # 高音 → 細かい振動
        hx = math.sin(t * 15.0 + self.x * 0.05) * high * 2.0
        hy = math.cos(t * 14.0 + self.y * 0.05) * high * 2.0

        # 外部風（マウス位置ベース）
        self.vx += (cx + tx + hx + wind_x * 0.3) * 0.15
        self.vy += (cy + ty + hy + wind_y * 0.3) * 0.15

        # ── 3. 速度制限 ───────────────────────────────────
        spd = math.hypot(self.vx, self.vy)
        max_spd = (2.0 + vol * 10.0)
        if spd > max_spd:
            self.vx = self.vx / spd * max_spd
            self.vy = self.vy / spd * max_spd

        # ── 4. 摩擦（音が大きいほど滑らか）──────────────
        friction = 0.97 - (1.0 - vol) * 0.04   # 0.93〜0.97
        self.vx *= friction
        self.vy *= friction

        # ── 5. 位置更新 ───────────────────────────────────
        self.trail.append((self.x, self.y))
        if len(self.trail) > TRAIL_LEN:
            self.trail.pop(0)

        self.x += self.vx * speed_boost * 0.4
        self.y += self.vy * speed_boost * 0.4

        # ── 6. 画面ループ（壁で跳ね返らず、逆側から出てくる）
        self.x = self.x % WIDTH
        self.y = self.y % HEIGHT

        # ── 7. 色相を音声でゆっくりずらす ─────────────────
        self.hue += mid * 2.0 + high * 4.0 + 0.3
        self.hue %= 360

        # ── 8. 寿命 ───────────────────────────────────────
        decay = 0.002 + vol * 0.005
        self.life -= decay
        if self.life <= 0:
            self._spawn()

    # ── 描画 ──────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, av: dict):
        vol  = av["volume"]
        bass = av["bass"]

        life_ratio = max(0, self.life / self.max_life)
        size = self.base_size * (1.0 + bass * 2.5)

        # 彩度・明度も音声で変化
        sat = 0.6 + av["mid"] * 0.4
        val = 0.5 + vol * 0.5

        color = self.hsv_to_rgb(self.hue, sat, val)

        # トレイル描画
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            ratio = (i + 1) / (n + 1)
            tr_size = max(1, int(size * ratio * 0.7))
            dim = ratio * life_ratio
            c = tuple(int(ch * dim * 0.6) for ch in color)
            try:
                pygame.draw.circle(surface, c, (int(tx), int(ty)), tr_size)
            except Exception:
                pass

        # 本体
        bright = tuple(min(255, int(ch * life_ratio)) for ch in color)
        try:
            pygame.draw.circle(surface, bright, (int(self.x), int(self.y)), max(1, int(size)))
        except Exception:
            pass


# ════════════════════════════════════════════════════════════
#  メイン
# ════════════════════════════════════════════════════════════
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("🎵 Audio Free Particle")
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("Arial", 14)

    # 描画バッファ（残像用）
    trail_surf = pygame.Surface((WIDTH, HEIGHT))
    trail_surf.fill((0, 0, 0))

    draw_surf  = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    particles = [Particle() for _ in range(NUM_PARTICLES)]

    # マイク起動
    mic_ok = False
    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=1,
            callback=_audio_cb,
        )
        stream.start()
        mic_ok = True
        print("✅ マイク開始")
    except Exception as e:
        print(f"⚠️  マイク失敗: {e}  →  デモモードで起動")

    t          = 0.0
    beat_flash = 0.0
    cx, cy     = WIDTH // 2, HEIGHT // 2  # マウス位置
    prev_beat  = False

    try:
        while True:
            # ── イベント ──────────────────────────────────
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return
                if ev.type == pygame.MOUSEMOTION:
                    cx, cy = ev.pos

            # ── 音声データ取得 ────────────────────────────
            av = get_audio()

            if not mic_ok:
                # デモモード
                av["volume"] = 0.25 + math.sin(t * 1.1) * 0.20
                av["bass"]   = 0.40 + math.sin(t * 0.9) * 0.30
                av["mid"]    = 0.30 + math.cos(t * 1.7) * 0.20
                av["high"]   = 0.15 + math.sin(t * 3.3) * 0.12
                av["beat"]   = int(t * 1.5) % 4 == 0 and (t * 1.5) % 1.0 < 0.05
                av["pitch"]  = 440.0

            # ── ビート処理 ────────────────────────────────
            if av["beat"] and not prev_beat:
                beat_flash = 1.0
                # ビート時：マウス周辺から粒子を爆発生成
                burst_count = 80
                for p in random.sample(particles, min(burst_count, len(particles))):
                    p._spawn(burst_x=cx, burst_y=cy)
            prev_beat  = av["beat"]
            beat_flash = max(0.0, beat_flash - 0.06)

            # ── マウス → 風ベクトル ───────────────────────
            wind_x = (cx - WIDTH  / 2) / (WIDTH  / 2) * 2.0
            wind_y = (cy - HEIGHT / 2) / (HEIGHT / 2) * 2.0

            # ── 残像フェード ──────────────────────────────
            # 音量が大きいほど残像を長く残す
            fade_alpha = int(18 + (1.0 - av["volume"]) * 22)
            fade_surf  = pygame.Surface((WIDTH, HEIGHT))
            fade_surf.set_alpha(fade_alpha)
            fade_surf.fill((0, 0, 8))
            screen.blit(fade_surf, (0, 0))

            # ── パーティクル更新・描画 ─────────────────────
            draw_surf.fill((0, 0, 0, 0))
            for p in particles:
                p.update(t, av, wind_x, wind_y)
                p.draw(draw_surf, av)
            screen.blit(draw_surf, (0, 0))

            # ── ビートフラッシュ ──────────────────────────
            if beat_flash > 0.02:
                fs = pygame.Surface((WIDTH, HEIGHT))
                fs.set_alpha(int(beat_flash * 50))
                # ピッチで色を変える
                p_hue = (av["pitch"] / 20.0) % 360 if av["pitch"] > 0 else 180
                r = int(128 + math.sin(math.radians(p_hue)) * 127)
                g = int(128 + math.sin(math.radians(p_hue + 120)) * 127)
                b = int(128 + math.sin(math.radians(p_hue + 240)) * 127)
                fs.fill((r, g, b))
                screen.blit(fs, (0, 0))

            # ── HUD ───────────────────────────────────────
            def bar(label, val, y_pos, color):
                pygame.draw.rect(screen, (20, 20, 40), (15, y_pos, 150, 8), border_radius=4)
                pygame.draw.rect(screen, color, (15, y_pos, int(150 * val), 8), border_radius=4)
                txt = font.render(f"{label}", True, (120, 140, 180))
                screen.blit(txt, (170, y_pos - 2))

            bar("VOL",  av["volume"], HEIGHT-50, (0, 220, 255))
            bar("BASS", av["bass"],   HEIGHT-40, (255, 100,  50))
            bar("MID",  av["mid"],    HEIGHT-20, (100, 255, 100))
            bar("HIGH", av["high"],   HEIGHT-10, (200, 100, 255))

            mode = "🎤 MIC" if mic_ok else "🔁 DEMO"
            screen.blit(font.render(mode, True, (150, 200, 255)), (WIDTH-80, HEIGHT-25))
            screen.blit(font.render("ESC: 終了 | マウス: 風向き", True, (60, 80, 120)), (WIDTH-230, 12))
            if av["beat"]:
                screen.blit(font.render("● BEAT", True, (255, 200, 50)), (15, HEIGHT-95))

            pygame.display.flip()
            clock.tick(FPS)
            t += 1.0 / FPS

    finally:
        if mic_ok:
            stream.stop()
            stream.close()
        pygame.quit()


if __name__ == "__main__":
    main()