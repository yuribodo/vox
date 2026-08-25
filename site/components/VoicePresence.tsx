"use client";

import {
  motion,
  motionValue,
  useAnimationFrame,
  useReducedMotion,
  useSpring,
  useTransform,
  type MotionValue,
} from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";

const BAR_COUNT = 56;
const bars = Array.from({ length: BAR_COUNT }, (_, index) => index);
const CYCLE = 8.4;
const LISTEN = 1.05;
const SPEAK = 4.1;
const SPRING = { stiffness: 140, damping: 18, mass: 0.5 };
const SAMPLE_EVERY_MS = 36;

type VoicePresenceProps = Readonly<{
  words: readonly string[];
}>;

function speechLevel(cycle: number) {
  if (cycle < LISTEN) return 0.12 + 0.04 * Math.sin(cycle * 2.1);
  if (cycle < LISTEN + SPEAK) {
    const t = cycle - LISTEN;
    const syllable =
      Math.pow(Math.max(0, Math.sin(t * 5.1)), 2.4) * 0.7 +
      Math.pow(Math.max(0, Math.sin(t * 2.7 + 0.9)), 3.1) * 0.45;
    const phrase = 0.4 + 0.6 * Math.sin(t * 0.7);
    const pause = Math.sin(t * 1.35) > -0.5 ? 1 : 0.08;
    return Math.min(1, 0.1 + syllable * phrase * pause);
  }
  return 0.08 + 0.03 * Math.sin(cycle * 1.1);
}

function nextSample(level: number, time: number) {
  const peak =
    Math.abs(Math.sin(time * 23.4)) * 0.42 +
    Math.abs(Math.sin(time * 11.6 + 0.8)) * 0.33 +
    Math.abs(Math.sin(time * 37.1 + 1.7)) * 0.25;
  const dip = 0.18 + 0.82 * Math.abs(Math.sin(time * 6.2 + 0.4));
  return 0.07 + level * peak * dip;
}

function WaveBar({ level }: { level: MotionValue<number> }) {
  const scale = useSpring(level, SPRING);
  const transform = useTransform(scale, (value) => `scaleY(${value})`);
  return <motion.i aria-hidden="true" style={{ transform }} />;
}

export function VoicePresence({ words }: VoicePresenceProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const playingRef = useRef(true);
  const lastSampleAt = useRef(0);
  const history = useRef(Array.from({ length: BAR_COUNT }, () => 0.1));
  const levels = useMemo(() => bars.map(() => motionValue(0.12)), []);
  const energy = useMemo(() => motionValue(0.14), []);
  const glow = useSpring(energy, SPRING);
  const waveGlow = useTransform(glow, (level) => 0.05 + level * 0.2);
  const reduceMotion = useReducedMotion() ?? false;
  const [visibleCount, setVisibleCount] = useState(0);
  const lastCount = useRef(0);
  const shownCount = reduceMotion ? words.length : visibleCount;

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const visibility = new IntersectionObserver(([entry]) => {
      playingRef.current = entry?.isIntersecting ?? true;
    }, { threshold: 0.12 });
    visibility.observe(root);
    return () => visibility.disconnect();
  }, []);

  useEffect(() => {
    if (!reduceMotion) return;
    history.current.forEach((unused, index) => {
      const rest = 0.16 + 0.2 * Math.abs(Math.sin(index * 0.55)) * Math.abs(Math.cos(index * 0.31));
      levels[index]?.set(rest);
    });
    energy.set(0.18);
  }, [energy, levels, reduceMotion]);

  useAnimationFrame((time) => {
    if (reduceMotion || !playingRef.current) return;

    const seconds = time / 1000;
    const cycle = seconds % CYCLE;
    const level = speechLevel(cycle);
    energy.set(level);

    if (time - lastSampleAt.current >= SAMPLE_EVERY_MS) {
      lastSampleAt.current = time;
      history.current.shift();
      history.current.push(nextSample(level, seconds));
      for (let index = 0; index < BAR_COUNT; index += 1) {
        levels[index]?.set(history.current[index] ?? 0.1);
      }
    }

    const spoken = cycle - LISTEN;
    const nextCount =
      cycle < LISTEN
        ? 0
        : cycle > LISTEN + SPEAK
          ? words.length
          : Math.min(words.length, Math.max(0, Math.floor(spoken / 0.12)));
    if (nextCount !== lastCount.current) {
      lastCount.current = nextCount;
      setVisibleCount(nextCount);
    }
  });

  return (
    <div
      ref={rootRef}
      className="voice-session"
      data-voice-presence
      aria-label="Spoken audio resolving into local text"
    >
      <div className="session-wave" aria-hidden="true">
        <motion.span className="session-wave-glow" style={{ opacity: waveGlow }} />
        {bars.map((index) => (
          <WaveBar key={index} level={levels[index]!} />
        ))}
      </div>
      <p className="session-transcript" aria-live="polite">
        {words.map((word, index) => (
          <motion.span
            key={`${word}-${index}`}
            initial={false}
            animate={
              index < shownCount
                ? { opacity: 1, transform: "translateY(0px)" }
                : { opacity: 0, transform: "translateY(8px)" }
            }
            transition={{ type: "spring", duration: 0.42, bounce: 0.12 }}
          >
            {word}
          </motion.span>
        ))}
      </p>
    </div>
  );
}
