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
          .from("[data-header]", { y: -8, autoAlpha: 0, duration: 0.42 })
          .from(".eyebrow", { y: 8, autoAlpha: 0, duration: 0.42 }, 0.1)
          .from("[data-hero-line]", {
            yPercent: 108,
            duration: 0.72,
            stagger: 0.075,
            ease: "power4.out",
          }, 0.16)
          .from(".hero-description", { y: 12, autoAlpha: 0, duration: 0.52 }, 0.42)
          .from(".hero-actions", { y: 10, autoAlpha: 0, duration: 0.48 }, 0.49)
          .from("[data-voice-presence]", { y: 12, autoAlpha: 0.35, duration: 0.64 }, 0.46);

        gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
          const targets = element.children.length > 1 ? Array.from(element.children) : element;
          gsap.from(targets, {
            y: 12,
            autoAlpha: 0,
            duration: 0.44,
            stagger: 0.05,
            ease: "power3.out",
            scrollTrigger: { trigger: element, start: "top 88%", once: true },
          });
        });

        gsap.from("[data-loop] > li", {
          y: 14,
          autoAlpha: 0,
          duration: 0.48,
          stagger: 0.08,
          ease: "power3.out",
          scrollTrigger: { trigger: "[data-loop]", start: "top 82%", once: true },
        });
      });

      return () => media.revert();
    }, rootRef);

    return () => context.revert();
  }, []);

  return <div ref={rootRef}>{children}</div>;
}
