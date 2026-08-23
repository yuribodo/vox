"use client";

import Image from "next/image";
import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "motion/react";
import type { PointerEvent } from "react";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function SpecimenPoster() {
  const reducedMotion = useReducedMotion();
  const pointerX = useMotionValue(0);
  const pointerY = useMotionValue(0);
  const smoothX = useSpring(pointerX, { stiffness: 160, damping: 24, mass: 0.6 });
  const smoothY = useSpring(pointerY, { stiffness: 160, damping: 24, mass: 0.6 });
  const rotateY = useTransform(smoothX, [-0.5, 0.5], [-1.2, 1.2]);
  const rotateX = useTransform(smoothY, [-0.5, 0.5], [1.2, -1.2]);
  const transform = useMotionTemplate`perspective(1400px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;

  const handlePointerMove = (event: PointerEvent<HTMLElement>) => {
    if (reducedMotion || event.pointerType === "touch") return;
    const bounds = event.currentTarget.getBoundingClientRect();
    pointerX.set((event.clientX - bounds.left) / bounds.width - 0.5);
    pointerY.set((event.clientY - bounds.top) / bounds.height - 0.5);
  };

  const resetPointer = () => {
    pointerX.set(0);
    pointerY.set(0);
  };

  return (
    <motion.figure
      className="specimen-poster"
      onPointerMove={handlePointerMove}
      onPointerLeave={resetPointer}
      style={reducedMotion ? undefined : { transform }}
    >
      <Image
        alt="Disassembled microphone, capsule, circuit board and cable arranged as a technical voice specimen"
        src={`${basePath}/images/voice-specimen.webp`}
        fill
        priority
        sizes="(max-width: 800px) 110vw, 88vw"
      />
      <figcaption>
        <span>FIG. V—001</span>
        <span>transduction study / 16 kHz</span>
      </figcaption>
      <div className="specimen-seal" aria-hidden="true"><span>LOCAL</span><span>ONLY</span></div>
    </motion.figure>
  );
}
