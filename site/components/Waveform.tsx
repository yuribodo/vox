"use client";

import { useEffect, useRef } from "react";

function wavePath(time: number) {
  const width = 720;
  const center = 130;
  const points = 120;
  let path = `M 0 ${center}`;

  for (let index = 1; index <= points; index += 1) {
    const x = (index / points) * width;
    const normalized = index / points;
    const envelope = Math.pow(Math.sin(normalized * Math.PI), 1.5);
    const carrier =
      Math.sin(index * 0.54 + time * 0.0021) * 0.46 +
      Math.sin(index * 1.12 - time * 0.0014) * 0.3 +
      Math.sin(index * 0.19 + time * 0.0018) * 0.24;
    const pulse = 0.58 + Math.sin(time * 0.001 + index * 0.03) * 0.16;
    const y = center + carrier * envelope * 106 * pulse;
    path += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
  }

  return path;
}

export function Waveform() {
  const lineRef = useRef<SVGPathElement>(null);
  const glowRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;

    const draw = (time = 0) => {
      const path = wavePath(time);
      lineRef.current?.setAttribute("d", path);
      glowRef.current?.setAttribute("d", path);
      if (!motionQuery.matches) frame = window.requestAnimationFrame(draw);
    };

    const handleMotionChange = () => {
      window.cancelAnimationFrame(frame);
      if (!motionQuery.matches) frame = window.requestAnimationFrame(draw);
    };

    draw();
    motionQuery.addEventListener("change", handleMotionChange);
    return () => {
      window.cancelAnimationFrame(frame);
      motionQuery.removeEventListener("change", handleMotionChange);
    };
  }, []);

  return (
    <svg viewBox="0 0 720 260" preserveAspectRatio="none">
      <defs>
        <linearGradient id="signal-fade" x1="0" x2="1">
          <stop offset="0" stopColor="#a6ff4d" stopOpacity="0" />
          <stop offset="0.12" stopColor="#a6ff4d" />
          <stop offset="0.88" stopColor="#a6ff4d" />
          <stop offset="1" stopColor="#a6ff4d" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path ref={glowRef} className="signal-glow" d={wavePath(0)} />
      <path ref={lineRef} className="signal-line" d={wavePath(0)} />
    </svg>
  );
}
