"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import type { ReactNode } from "react";
import { useEffect, useRef } from "react";

export function LandingMotion({ children }: Readonly<{ children: ReactNode }>) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!rootRef.current) return;

    gsap.registerPlugin(ScrollTrigger);

    const context = gsap.context(() => {
      const media = gsap.matchMedia();

      media.add("(prefers-reduced-motion: no-preference)", () => {
        const intro = gsap.timeline({ defaults: { ease: "power3.out" } });
        intro
          .from("[data-specimen]", { clipPath: "inset(0 100% 0 0)", duration: 1.25 })
          .from("[data-intro]", { y: 24, autoAlpha: 0, duration: 0.72, stagger: 0.075 }, "-=0.72")
          .from(".hero-calibration i", { scaleX: 0, duration: 0.8 }, "-=0.45");

        gsap.to("[data-specimen]", {
          yPercent: -5,
          rotate: 0.8,
          ease: "none",
          scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: 0.6 },
        });

        gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
          gsap.from(element, {
            y: 36,
            autoAlpha: 0,
            duration: 0.9,
            ease: "power3.out",
            scrollTrigger: { trigger: element, start: "top 84%", once: true },
          });
        });

        const path = document.querySelector<SVGPathElement>("[data-voice-path]");
        if (path) {
          const length = path.getTotalLength();
          gsap.set(path, { strokeDasharray: length, strokeDashoffset: length });
          gsap.to(path, {
            strokeDashoffset: 0,
            duration: 1.35,
            ease: "power2.inOut",
            scrollTrigger: { trigger: ".signal-stage", start: "top 72%", once: true },
          });
        }

        const frames = gsap.utils.toArray<HTMLElement>("[data-signal-frame]");
        const steps = gsap.utils.toArray<HTMLElement>("[data-process-step]");
        const progress = document.querySelector<HTMLElement>("[data-signal-progress]");

        steps.forEach((step, index) => {
          ScrollTrigger.create({
            trigger: step,
            start: "top 58%",
            end: "bottom 42%",
            onToggle: ({ isActive }) => {
              if (!isActive) return;

              steps.forEach((item, itemIndex) => item.classList.toggle("is-active", itemIndex === index));
              frames.forEach((frame, frameIndex) => {
                frame.classList.toggle("is-active", frameIndex === index);
                gsap.to(frame, {
                  autoAlpha: frameIndex === index ? 1 : 0,
                  y: frameIndex === index ? 0 : 14,
                  duration: 0.42,
                  ease: "power2.out",
                  overwrite: true,
                });
              });

              if (progress) {
                gsap.to(progress, { scaleX: (index + 1) / steps.length, duration: 0.55, ease: "power3.out" });
              }
            },
          });
        });

        gsap.to("[data-signal-beam]", {
          xPercent: 520,
          ease: "none",
          scrollTrigger: { trigger: ".process-body", start: "top 70%", end: "bottom 35%", scrub: true },
        });

        gsap.from("[data-install-stamp] span", {
          yPercent: 110,
          rotate: 8,
          stagger: 0.08,
          duration: 0.85,
          ease: "power3.out",
          scrollTrigger: { trigger: ".install", start: "top 72%", once: true },
        });
      });

      return () => media.revert();
    }, rootRef);

    return () => context.revert();
  }, []);

  return <div ref={rootRef}>{children}</div>;
}
