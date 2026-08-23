"use client";

import { motion, useReducedMotion } from "motion/react";
import type { HTMLMotionProps } from "motion/react";
import type { ReactNode } from "react";

type MotionLinkProps = Readonly<
  HTMLMotionProps<"a"> & { children: ReactNode; href: string }
>;

export function MotionLink({ children, ...props }: MotionLinkProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.a
      {...props}
      whileHover={reduceMotion ? undefined : { y: -2 }}
      whileTap={reduceMotion ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 520, damping: 34 }}
    >
      {children}
    </motion.a>
  );
}
