"use client";

import { useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";

type CopyCommandProps = Readonly<{ command: string }>;

async function copyText(text: string) {
  if (!navigator.clipboard) throw new Error("Clipboard API unavailable");
  await navigator.clipboard.writeText(text);
}

export function CopyCommand({ command }: CopyCommandProps) {
  const [label, setLabel] = useState("copy");
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reduceMotion = useReducedMotion();

  const handleCopy = async () => {
    try {
      await copyText(command);
      setLabel("copied");
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => setLabel("copy"), 1600);
    } catch {
      setLabel("select text");
    }
  };

  return (
    <motion.button
      className={`copy-button${label === "copied" ? " is-copied" : ""}`}
      type="button"
      onClick={handleCopy}
      aria-label={`Copy command: ${command}`}
      whileTap={reduceMotion ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 520, damping: 34 }}
    >
      <span aria-live="polite">{label}</span>
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <rect x="6" y="6" width="10" height="10" rx="1" />
        <path d="M4 13H3V3h10v1" />
      </svg>
    </motion.button>
  );
}
